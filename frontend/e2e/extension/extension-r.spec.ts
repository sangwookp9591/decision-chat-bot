import { appendFileSync, existsSync, readFileSync } from 'node:fs';
import { expect, test, type APIRequestContext, type Browser, type Page } from '@playwright/test';

/**
 * T38-R browser checks for the fixes made after the first T38 run (F3 trace rule table, F4 blocked_by_invariant, F5 자료 부족 acknowledgement,
 * evidence layer for text-only requests, lead_org path, X08 validation card from the server). Compares screens with the public APIs and with the
 * Neo4j-derived export (db_truth.<phase>.json).
 *
 *   X38_OUT=<artifact dir> X38_TENANT=<tenant> X38_PHASE=r1|r3 E2E_API=http://127.0.0.1:<port> E2E_PORT=<port> npx playwright test -c playwright.extension-r.config.ts
 */
const OUT = process.env.X38_OUT as string;
const tenant = process.env.X38_TENANT as string;
const phase = process.env.X38_PHASE || 'r1';
const password = process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me';
const hasFixture = Boolean(OUT && tenant && existsSync(`${OUT}/state.json`) && existsSync(`${OUT}/db_truth.${process.env.X38_TRUTH || phase}.json`));
test.beforeAll(() => expect(hasFixture, 'X38 extension-R fixture 없음: X38_OUT/X38_TENANT를 설정하고 extension scenario의 state.json 및 db_truth export를 먼저 준비해야 함: scripts/e2e/run.py').toBe(true));
const state = hasFixture ? JSON.parse(readFileSync(`${OUT}/state.json`, 'utf8')) : {};
const truth = hasFixture ? JSON.parse(readFileSync(`${OUT}/db_truth.${process.env.X38_TRUTH || phase}.json`, 'utf8')) : { applied: [] };
const shot = (page: Page, name: string) => page.screenshot({ path: `${OUT}/screenshots/${phase}-${name}.png`, fullPage: false });

function note(data: unknown) { test.info().annotations.push({ type: 'evidence', description: JSON.stringify(data) }); }
test.afterEach(async ({}, info) => {
  const evidence = info.annotations.filter((a) => a.type === 'evidence').map((a) => JSON.parse(a.description || 'null'));
  appendFileSync(`${OUT}/ui-results.jsonl`, JSON.stringify({ phase, title: info.title, status: info.status, error: info.error?.message?.split('\n')[0], evidence, at: new Date().toISOString() }) + '\n');
});

async function as(browser: Browser, baseURL: string, role: string, tenantId = tenant) {
  const ctx = await browser.newContext({ baseURL });
  const r = await ctx.request.post('/api/auth/login', { data: { email: `${role}@${tenantId}.dev`, password } });
  expect(r.ok(), `login ${role}@${tenantId}`).toBeTruthy();
  return ctx;
}
const get = async (api: APIRequestContext, path: string) => (await api.get(path)).json();
const jsonText = (v: unknown) => JSON.stringify(v);

/** Open the Trace of a run, open its "규칙 적용" step and compare the drawer table with the step API (and the stored APPLIED rows). */
async function traceRuleTable(page: Page, api: APIRequestContext, requestId: string, runId: string, stepId: string, dbApplied: any[]) {
  await page.goto(`/observatory?request_id=${requestId}&run_id=${runId}`);
  await page.locator('.obs-node').filter({ has: page.getByText('규칙 적용', { exact: true }) }).click();
  const drawer = page.getByRole('dialog', { name: 'Trace 상세' });
  await expect(drawer).toContainText(`실행 ${runId}`);
  await expect(drawer).toContainText(stepId);
  const apiStep = await get(api, `/api/observe/steps/${stepId}`) as any;
  const section = drawer.getByRole('region', { name: '규칙 적용' });
  await expect(section).toBeVisible();
  const rows = section.locator('tbody tr');
  await expect(rows).toHaveCount(apiStep.rule_applications.length);
  expect(apiStep.rule_applications.length).toBe(dbApplied.length);
  const shown: unknown[] = [];
  for (const a of apiStep.rule_applications) {
    const row = rows.filter({ hasText: a.rule_version }).first();
    await expect(row).toContainText(a.outcome);
    await expect(row.locator('td').nth(3)).toHaveText(jsonText(a.before));
    await expect(row.locator('td').nth(4)).toHaveText(jsonText(a.after));
    const db = dbApplied.find((d: any) => d.rule === a.rule_version);
    expect(db, `stored APPLIED row for ${a.rule_version}`).toBeTruthy();
    expect(db.outcome).toBe(a.outcome);
    expect(db.before).toBe(jsonText(a.before));
    expect(db.after).toBe(jsonText(a.after));
    shown.push({ rule: a.rule_version, outcome: a.outcome, before: a.before, after: a.after });
  }
  return shown;
}
const appliedRows = (stepId: string) => truth.applied.filter((a: any) => a.step === stepId);

test.describe(`[${phase}] T38-R fixes`, () => {
  test.skip(phase !== 'r1', 'r1 phase only');

  test('[F3][X05] Observatory Trace "규칙 적용" step detail lists rule_id@version, outcome and before/after for every rule (used, out_of_scope, multi-rule) = step API = stored APPLIED', async ({ browser, baseURL }) => {
    test.setTimeout(120_000);
    const ctx = await as(browser, baseURL as string, 'reviewer');
    const page = await ctx.newPage();
    const out: Record<string, unknown> = {};
    const pr = state.post_requests;
    const cases: [string, string, string, string][] = [
      ['used', pr.in_scope[0], pr.report[pr.in_scope[0]].run_id, pr.report[pr.in_scope[0]].step_ids_in_applied[0]],
      ['out_of_scope', pr.out_of_scope, pr.report[pr.out_of_scope].run_id, pr.report[pr.out_of_scope].step_ids_in_applied[0]],
    ];
    for (const key of ['rule_lead', 'rule2']) {
      const p = state[key].post_request;
      cases.push([`${key}_${state[key].field}`, p.request_id, p.run_id, p.applied[0].step]);
    }
    for (const [label, rid, run, step] of cases) {
      out[label] = { request: rid, run, step, rows: await traceRuleTable(page, ctx.request, rid, run, step, appliedRows(step)) };
      await shot(page, `f3-trace-${label}`);
    }
    note(out);
  });

  test('[F4] Trace shows blocked_by_invariant for the violating rules written straight into the DB; the classification stays the model value', async ({ browser, baseURL }) => {
    const ctx = await as(browser, baseURL as string, 'reviewer', state.invariants.tenant);
    const page = await ctx.newPage();
    const inv = state.invariants;
    const dbApplied = truth.inv_applied.filter((a: any) => a.step === inv.step);
    expect(dbApplied.length).toBe(2);
    const shown = await traceRuleTable(page, ctx.request, inv.request, inv.run, inv.step, dbApplied);
    for (const s of shown as any[]) expect(s.outcome).toBe('blocked_by_invariant');
    await expect(page.getByRole('dialog', { name: 'Trace 상세' }).getByRole('region', { name: '규칙 적용' })).toContainText('blocked_by_invariant');
    await shot(page, 'f4-blocked-by-invariant');
    note({ tenant: inv.tenant, request: inv.request, shown });
  });

  test('[F5] 자료 부족 candidate: approve is disabled until the acknowledgement checkbox and a ≥10 character reason; afterwards "자료 부족 상태로 승인됨" is shown', async ({ browser, baseURL }) => {
    test.setTimeout(90_000);
    const ctx = await as(browser, baseURL as string, 'rule_admin');
    const page = await ctx.newPage();
    const proposer = await as(browser, baseURL as string, 'reviewer');
    const csrf = (await proposer.storageState()).cookies.find(c => c.name === 'jev_csrf')!.value;
    const created = await proposer.request.post('/api/learning/candidates', { headers: { 'X-CSRF-Token': csrf }, data: { field: 'ai_need', proposed_action: { set: '혼합' }, scope: { all: [{ field: 'lead_org', op: 'eq', value: '현업' }] }, rationale: '브라우저별 독립 자료 부족 승인 시험', supporting_correction_ids: [] } });
    expect(created.status()).toBe(201);
    const cid = (await created.json()).id as string;
    await proposer.close();
    await page.goto(`/learning?candidate_id=${cid}`);
    await expect(page.getByRole('heading', { name: '규칙 학습', exact: true })).toBeVisible();
    await expect(page.getByText('자료 부족: 효과를 주장하지 않습니다.')).toBeVisible();
    const approve = page.getByRole('button', { name: '승인', exact: true });
    const reason = page.getByLabel('결정 사유');
    const ack = page.getByLabel('자료 부족 상태임을 확인');
    await page.getByLabel('규칙 ID').fill(`R-BROWSER-${Date.now()}`);
    await reason.fill('T38-R 화면 시험: 지지 수정 0건 확인');
    await expect(approve).toBeDisabled();                         // reason ok, acknowledgement missing
    await expect(page.getByText('비활성: 자료 부족 확인 체크와 10자 이상 사유가 필요합니다.').first()).toBeVisible();
    await shot(page, 'f5-disabled-without-ack');
    await ack.focus(); await ack.press('Space');
    await reason.fill('짧은 사유');
    await expect(approve).toBeDisabled();                         // acknowledgement ok, reason too short
    await reason.fill('T38-R 화면 시험: 지지 수정 0건 확인');
    await expect(approve).toBeEnabled();
    await approve.click();
    await expect(page.getByText('자료 부족 상태로 승인됨').first()).toBeVisible();
    await shot(page, 'f5-approved-label');
    const api = await get(ctx.request, `/api/learning/candidates/${cid}`) as any;
    expect(api.insufficient_approved).toBe(true);
    expect(api.insufficient_approval_label).toBe('자료 부족 상태로 승인됨');
    note({ candidate: cid, api_label: api.insufficient_approval_label, status: api.status });
  });

  test('[EVID][X06] text-only request: chat EvidenceSpan nodes are on the map (evidence layer), the cited span is reachable from the business step on the map', async ({ browser, baseURL }) => {
    test.setTimeout(120_000);
    const ctx = await as(browser, baseURL as string, 'rule_admin');
    const page = await ctx.newPage();
    const ev = state.evidence_layer;
    const api = await get(ctx.request, `/api/graph/judgment?request_id=${ev.request}`) as any;
    const apiSpans: string[] = api.nodes.filter((n: any) => n.kind === 'EvidenceSpan').map((n: any) => n.id);
    for (const id of ev.cited) expect(apiSpans).toContain(id);
    await page.goto(`/judgment-map?request_id=${ev.request}`);
    await expect(page.getByRole('heading', { name: '입체 판단 맵' })).toBeVisible();
    const board = page.getByTestId('jm-board');
    await expect(board).toHaveAttribute('data-node-count', String(api.node_count));
    const group = page.locator('.jm-node.is-group[data-kind="EvidenceSpan"]');
    if (await group.count()) { await expect(group.first()).toContainText(String(apiSpans.length)); await group.first().click(); }
    await expect(page.locator('.jm-node[data-kind="EvidenceSpan"]:not(.is-group)').first()).toBeVisible();
    const shownSpans: string[] = await page.locator('.jm-node[data-kind="EvidenceSpan"]:not(.is-group)').evaluateAll((els) => els.map((el) => (el as HTMLElement).dataset.nodeId as string));
    expect(new Set(shownSpans)).toEqual(new Set(apiSpans));
    for (const id of ev.cited) await expect(page.locator(`.jm-node[data-node-id="${id}"]`)).toBeVisible();
    const stepId = state.trace.step;
    await page.locator(`.jm-node[data-node-id="${stepId}"]`).click();
    await expect(page.locator('.jm-node[data-kind="EvidenceSpan"].is-path').first()).toBeVisible();
    await shot(page, 'evid-chat-span-trace');
    const stored = (truth.chat_spans || []).filter((s: any) => ev.cited.includes(s.id));
    expect(stored.length).toBe(ev.cited.length);
    for (const s of stored) expect(s.source).toBe('chat');
    note({ request: ev.request, span_nodes_on_map: shownSpans, cited: ev.cited, stored_sources: stored.map((s: any) => s.source) });
  });

  test('[X02][X05] lead_org rule on the learning screen: candidate → decision → version → shadow validation → published, application count = stored APPLIED', async ({ browser, baseURL }) => {
    test.setTimeout(90_000);
    const ctx = await as(browser, baseURL as string, 'rule_admin');
    const page = await ctx.newPage();
    const lead = state.rule_lead;
    const ver = truth.rule_versions.find((v: any) => v.id === lead.ref);
    await page.goto(`/learning?candidate_id=${lead.candidate}`);
    await expect(page.getByRole('heading', { name: '규칙 학습', exact: true })).toBeVisible();
    await expect(page.getByText(`버전 ${lead.ref} ·`)).toContainText(`적용 기록 ${ver.applications}`);
    const card = page.getByRole('region', { name: '비교 검증' });
    const val = truth.validations.find((v: any) => v.id === lead.validation);
    await expect(card.locator('h3 .mono')).toHaveText(val.id);
    await expect(card).toContainText(`부작용 ${val.side_effects}건`);
    const tl = page.locator('.learning-timeline');
    for (const kind of ['후보 제안', '비교 검증', '게시 · 운영 중']) await expect(tl).toContainText(kind);
    await expect(tl).toContainText(`Config v${lead.config}`);
    const body = JSON.parse(ver.body);
    expect(body.target).toBe('lead_org');
    expect(body.action).toEqual({ set: lead.target });
    await shot(page, 'lead-org-learning');
    note({ rule: lead.ref, action: body.action, applications: ver.applications, validation: val.id });
  });
});

test.describe(`[${phase}] X08 after restart`, () => {
  test.skip(phase !== 'r3', 'r3 phase only');

  test('[X08][F6] validation card is read from the server after API/worker restart and a reload: id, sample, changed, side effects, calls = DB = API; shadow Run id differs from the ValidationRun id', async ({ browser, baseURL }) => {
    test.setTimeout(120_000);
    const ctx = await as(browser, baseURL as string, 'rule_admin');
    const page = await ctx.newPage();
    const val = truth.validations.find((v: any) => v.id === state.validation_id);
    const apiVal = await get(ctx.request, `/api/learning/validations/${val.id}`) as any;
    for (const k of ['sample_count', 'labeled_count', 'changed_count', 'side_effects', 'calls', 'max_calls', 'status']) expect(apiVal[k]).toBe(val[k]);
    const check = async () => {
      await expect(page.getByRole('heading', { name: '규칙 학습', exact: true })).toBeVisible();
      await page.getByLabel('규칙 버전').selectOption(String(state.rule_version));
      const card = page.getByRole('region', { name: '비교 검증' });
      await expect(card.locator('h3 .mono')).toHaveText(val.id);
      await expect(card).toContainText(`표본 ${val.sample_count}건 · 사람 확정 정답 ${val.labeled_count}건`);
      await expect(card).toContainText(`${val.changed_count} / ${val.sample_count}`);
      await expect(card).toContainText(`부작용 ${val.side_effects}건`);
      await expect(card).toContainText(`호출 ${val.calls}/${val.max_calls}`);
    };
    await page.goto(`/learning?candidate_id=${state.cand_y}`);
    await check();
    await page.reload();
    await check();
    await shot(page, 'x08-validation-card-after-restart');
    const runs = truth.shadow_runs as any[];
    expect(runs.length).toBeGreaterThan(0);
    for (const r of runs) { expect(r.run_id).not.toBe(r.validation_id); expect(r.run_id.startsWith('run_shadow_')).toBe(true); expect(r.kind).toBe('shadow'); }
    note({ validation: val.id, api: { sample: apiVal.sample_count, changed: apiVal.changed_count, side: apiVal.side_effects }, shadow_runs: runs.length });
  });
});
