import { appendFileSync, readFileSync } from 'node:fs';
import { expect, test, type APIRequestContext, type Browser, type Page } from '@playwright/test';

/**
 * T38 extension scenario — browser side. Compares what the screens show with (a) the stored Neo4j truth exported by
 * backend/tests/acceptance/extension/scenario.py (db_truth.<phase>.json, read straight from the database) and (b) the public APIs.
 *
 *   X38_OUT=<artifact dir> X38_TENANT=<tenant> X38_PHASE=ui1|ui2|ui3 E2E_API=http://127.0.0.1:<port> E2E_PORT=<port> \
 *     npx playwright test -c playwright.extension.config.ts
 */
const OUT = process.env.X38_OUT as string;
const tenant = process.env.X38_TENANT as string;
const phase = process.env.X38_PHASE || 'ui1';
const password = process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me';
const state = JSON.parse(readFileSync(`${OUT}/state.json`, 'utf8'));
const truth = JSON.parse(readFileSync(`${OUT}/db_truth.${process.env.X38_TRUTH || phase}.json`, 'utf8'));
const shot = (page: Page, name: string) => page.screenshot({ path: `${OUT}/screenshots/${phase}-${name}.png`, fullPage: false });

function note(data: unknown) { test.info().annotations.push({ type: 'evidence', description: JSON.stringify(data) }); }
test.afterEach(async ({}, info) => {
  const evidence = info.annotations.filter((a) => a.type === 'evidence').map((a) => JSON.parse(a.description || 'null'));
  appendFileSync(`${OUT}/ui-results.jsonl`, JSON.stringify({ phase, title: info.title, status: info.status, error: info.error?.message?.split('\n')[0], evidence, at: new Date().toISOString() }) + '\n');
});

async function login(api: APIRequestContext, role: string) {
  const r = await api.post('/api/auth/login', { data: { email: `${role}@${tenant}.dev`, password } });
  expect(r.ok(), `login ${role}`).toBeTruthy();
}
async function as(browser: Browser, baseURL: string, role: string) {
  const ctx = await browser.newContext({ baseURL });
  await login(ctx.request, role);
  return ctx;
}
const when = (page: Page, iso: string) => page.evaluate((v) => new Date(v).toLocaleString('ko-KR', { hour12: false }), iso);
const get = async (api: APIRequestContext, path: string) => (await api.get(path)).json();

const candY: string = state.cand_y;
const candZ: string = state.cand_z;
const dbCand = (id: string) => truth.candidates.find((c: any) => c.id === id);
const supportCorrections = truth.corrections.filter((c: any) => state.seed.plan.same_direction.includes(c.request_id));

test.describe(`[${phase}] before stop`, () => {
  test.skip(phase !== 'ui1', 'ui1 phase only');

  test('[X01][X02] reviewer sees AI original vs correction with who/when/revision/run/Config, support & counter examples, 자료 부족', async ({ browser, baseURL }) => {
    const ctx = await as(browser, baseURL as string, 'reviewer');
    const page = await ctx.newPage();
    await page.goto(`/learning?candidate_id=${candY}`);
    await expect(page.getByRole('heading', { name: '규칙 학습', exact: true })).toBeVisible();
    const table = page.getByRole('table', { name: '근거 수정 기록' });
    await expect(table).toBeVisible();
    const rowsOut: unknown[] = [];
    for (const c of supportCorrections) {
      const row = table.getByRole('row').filter({ hasText: c.request_id });
      await expect(row).toHaveCount(1);
      await expect(row).toContainText(`AI 필요성: ${JSON.parse(c.ai_value)} → ${JSON.parse(c.corrected_value)}`);
      await expect(row).toContainText(c.corrected_by);
      await expect(row).toContainText(await when(page, c.corrected_at));
      await expect(row).toContainText(`${c.revision_id} · ${c.run_id} · v${c.config_version}`);
      await expect(row).toContainText('지지');
      rowsOut.push({ request: c.request_id, correction: c.id, run: c.run_id, revision: c.revision_id, config: c.config_version });
    }
    const dbSupport = dbCand(candY).links.filter((l: any) => l.role === 'support').length;
    const dbCounter = dbCand(candY).links.filter((l: any) => l.role === 'counter').length;
    await expect(table.getByText('지지', { exact: true })).toHaveCount(dbSupport);
    await expect(table.getByText('반례', { exact: true })).toHaveCount(dbCounter);
    const unc = JSON.parse(dbCand(candY).unc);
    await expect(page.getByText(`지지 ${unc.support_count}건 · 반례 ${unc.counter_count}건 · 최소 ${unc.minimum_support}건`)).toBeVisible();
    await expect(page.getByText('적용 범위 (제안)')).toBeVisible();
    await shot(page, 'x01-x02-candidate-support');
    note({ candidate: candY, support_rows: rowsOut, db_support: dbSupport, db_counter: dbCounter, uncertainty: unc });

    // 자료 부족 candidate (two corrections only)
    await page.getByRole('button', { name: new RegExp(candZ) }).click();
    // (T38-R) this candidate was approved earlier by the F5 stage with the explicit '자료 부족' acknowledgement
    await expect(page.getByText('자료 부족 상태로 승인됨').first()).toBeVisible();
    expect(dbCand(candZ).status).toBe('approved');
    await expect(page.getByRole('table', { name: '근거 수정 기록' }).getByText('지지', { exact: true })).toHaveCount(dbCand(candZ).links.filter((l: any) => l.role === 'support').length);
    await shot(page, 'x02-insufficient');
    // Non-admin: every administrator action disabled with a reason, single-review approval is not a rule publication.
    await expect(page.getByRole('button', { name: '승인', exact: true })).toBeDisabled();
    await expect(page.getByText('규칙 관리자만 실행할 수 있습니다.').first()).toBeVisible();
    await expect(page.getByText('요청 한 건의 수정 승인은 규칙 게시가 아닙니다.')).toBeVisible();
    note({ insufficient_candidate: candZ, db_status: dbCand(candZ).status, reviewer_buttons_disabled: true });
  });

  test('[X03] requester has no access to rule learning; no rule actions exposed', async ({ browser, baseURL }) => {
    const ctx = await as(browser, baseURL as string, 'requester');
    const page = await ctx.newPage();
    await page.goto('/learning');
    await expect(page.getByText('조회 권한이 없습니다')).toBeVisible();
    await expect(page.getByRole('button', { name: '게시', exact: true })).toHaveCount(0);
    await shot(page, 'x03-requester-denied');
  });

  test('[X03][X04][X09] rule admin: confirmed scope, validation card = DB, lifecycle timeline, observation counts = effects API = DB, 표본 부족', async ({ browser, baseURL }) => {
    const ctx = await as(browser, baseURL as string, 'rule_admin');
    const page = await ctx.newPage();
    const rule1 = truth.rule_versions.find((v: any) => v.id === state.ref);
    await page.goto(`/learning?candidate_id=${candY}`);
    await expect(page.getByText('적용 범위 (확정)')).toBeVisible();
    await expect(page.getByText(new RegExp(`상태 게시 · 운영 중|상태 게시`)).first()).toBeVisible();
    await expect(page.getByText(`버전 ${state.ref} ·`)).toContainText(`적용 기록 ${rule1.applications}`);
    // Validation card == DB ValidationRun
    const val = truth.validations.find((v: any) => v.id === state.validation_id);
    const card = page.getByRole('region', { name: '비교 검증' });
    await expect(card.locator('h3 .mono')).toHaveText(val.id);
    await expect(card).toContainText(`표본 ${val.sample_count}건 · 사람 확정 정답 ${val.labeled_count}건`);
    await expect(card).toContainText(`${val.changed_count} / ${val.sample_count}`);
    await expect(card).toContainText(`부작용 ${val.side_effects}건`);
    await expect(card).toContainText(`호출 ${val.calls}/${val.max_calls}`);
    // Lifecycle timeline
    const tl = page.locator('.learning-timeline');
    for (const kind of ['후보 제안', '범위 수정 후 승인', '비교 검증', '게시 · 운영 중']) await expect(tl).toContainText(kind);
    await expect(tl).toContainText(`Config v${state.pub_config}`);
    await shot(page, 'x03-x04-admin-card-timeline');
    // Observation (X09): UI == effects API == independent DB computation
    const api = await get(ctx.request, `/api/learning/rules/${state.rule_id}/effects`);
    const db = truth.effects[state.rule_id];
    await expect(page.getByTestId('used-count')).toHaveText(String(api.groups.used.sample_count));
    await expect(page.getByTestId('out-count')).toHaveText(String(api.groups.out_of_scope.sample_count));
    expect(api.groups.used.sample_count).toBe(db.used.sample_count);
    expect(api.groups.out_of_scope.sample_count).toBe(db.out_of_scope.sample_count);
    expect(api.before_after.before.sample_count).toBe(db.before.sample_count);
    expect(api.before_after.after.sample_count).toBe(db.after.sample_count);
    await expect(page.getByTestId('effect-verdict')).toHaveText('관찰 중 · 표본 부족');
    await expect(page.getByText(/표본 부족: \d+건 \/ 최소 \d+건/)).toBeVisible();
    const obs = page.getByRole('region', { name: '게시 후 관찰' });
    await expect(obs).toContainText(`게시 전 (n=${db.before.sample_count})`);
    await expect(obs).toContainText(`게시 후 (n=${db.after.sample_count})`);
    await expect(obs).toContainText(`사용 (n=${db.used.sample_count})`);
    await expect(obs).toContainText(`범위 밖 (n=${db.out_of_scope.sample_count})`);
    await expect(obs).toContainText(`${db.used.corrections} / ${db.used.sample_count}`);
    await expect(obs).toContainText('기존 SLO 분모와 별도 지표');
    await shot(page, 'x09-observation');
    note({ ui_used: api.groups.used.sample_count, ui_out: api.groups.out_of_scope.sample_count, db, api_effect: api.effect, minimum_sample: api.minimum_sample });
  });

  test('[X05] Trace: "규칙 적용" step of an in-scope run shows the stored judgment; out-of-scope run keeps the model value', async ({ browser, baseURL }) => {
    const ctx = await as(browser, baseURL as string, 'reviewer');
    const page = await ctx.newPage();
    const used = state.post_requests.in_scope[0];
    const oos = state.post_requests.out_of_scope;
    const rep = state.post_requests.report;
    const out: Record<string, unknown> = {};
    for (const [label, rid, expectAi] of [['used', used, '필요'], ['out_of_scope', oos, '불필요']] as const) {
      await page.goto(`/observatory?request_id=${rid}&run_id=${rep[rid].run_id}`);
      await page.getByRole('button', { name: /규칙 적용/ }).click();
      const drawer = page.getByRole('dialog', { name: 'Trace 상세' });
      await expect(drawer).toContainText(`실행 ${rep[rid].run_id}`);
      await expect(drawer).toContainText(`설정 v${state.pub_config}`);
      await expect(drawer).toContainText(rep[rid].step_ids_in_applied[0]);
      await expect(drawer).toContainText(`"ai_need": "${expectAi}"`);
      const text = await drawer.innerText();
      out[label] = { request: rid, run: rep[rid].run_id, step: rep[rid].step_ids_in_applied[0], shows_rule_version: text.includes(state.ref), shows_before_after: /APPLIED|before|이전 값/.test(text) };
      await shot(page, `x05-trace-${label}`);
      const dbApplied = truth.applied.filter((a: any) => a.step === rep[rid].step_ids_in_applied[0] && a.rule === state.ref);
      expect(dbApplied.length).toBe(1);
      expect(dbApplied[0].outcome).toBe(label);
    }
    note(out);
  });

  test('[X06] judgment map: nodes/edges = graph API = DB, bottom-up trace to source span, top-down trace, list view keyboard, Flow/Topology/Learning IDs', async ({ browser, baseURL }) => {
    test.setTimeout(150_000);
    const ctx = await as(browser, baseURL as string, 'rule_admin');
    const page = await ctx.newPage();
    const r2 = state.rule2, post = r2.post_request, snap = state.graph_snapshot;
    const api = await get(ctx.request, `/api/graph/judgment?request_id=${post.request_id}`) as any;
    // counts equal the DB-verified snapshot taken by the Python stage (graph API == Neo4j relationships)
    expect(api.node_count).toBe(snap.request.node_count);
    expect(api.edge_count).toBe(snap.request.edge_count);
    await page.goto(`/judgment-map?request_id=${post.request_id}`);
    await expect(page.getByRole('heading', { name: '입체 판단 맵' })).toBeVisible();
    const board = page.getByTestId('jm-board');
    await expect(board).toHaveAttribute('data-node-count', String(api.node_count));
    await expect(board).toHaveAttribute('data-edge-count', String(api.edge_count));
    for (const layer of api.layers) await expect(page.getByTestId(`jm-layer-count-${layer.layer}`)).toContainText(String(layer.count));
    const mapIds: string[] = await page.locator('.jm-node:not(.is-group)').evaluateAll((els) => els.map((el) => (el as HTMLElement).dataset.nodeId as string));
    for (const id of mapIds) expect(api.nodes.map((n: any) => n.id)).toContain(id);
    await shot(page, 'x06-map-request');
    // bottom-up: RunStep -> ... -> EvidenceSpan
    const step = page.locator(`.jm-node[data-node-id="${state.trace.step}"]`);
    await expect(step).toBeVisible();
    await step.click();
    await expect(page.getByTestId('jm-detail')).toContainText('5계층');
    await expect(page.getByTestId('jm-up-count')).toContainText(/근거 쪽으로 [1-9]\d*개/);
    const apiUp = await get(ctx.request, `/api/graph/judgment/path?node_id=${state.trace.step}&direction=up&depth=8&limit=200`) as any;
    for (const kind of ['RuleVersion', 'RuleDecision', 'RuleCandidate', 'Correction', 'ModelOutput', 'EvidenceSpan']) {
      await expect(page.locator(`.jm-node[data-kind="${kind}"].is-path`).first(), `${kind} highlighted on the up path`).toBeVisible();
      expect(apiUp.nodes.map((n: any) => n.kind)).toContain(kind);
    }
    for (const id of Object.values(state.trace.chain) as string[]) await expect(page.locator(`.jm-node[data-node-id="${id}"]`)).toBeAttached();
    await shot(page, 'x06-up-trace');
    await page.keyboard.press('Escape');
    // top-down: source span -> rule version -> business step (the span belongs to the rule's map, not the new request's)
    await page.goto(`/judgment-map?rule_id=${encodeURIComponent(r2.ref)}`);
    await expect(page.getByTestId('jm-board')).toHaveAttribute('data-node-count', String(snap.rule2.node_count));
    await expect(page.getByTestId('jm-board')).toHaveAttribute('data-edge-count', String(snap.rule2.edge_count));
    const span = page.locator(`.jm-node[data-node-id="${state.trace.span}"]`);
    await span.click();
    await expect(page.getByTestId('jm-down-count')).toContainText(/실행 쪽으로 [1-9]\d*개/);
    const apiDown = await get(ctx.request, `/api/graph/judgment/path?node_id=${state.trace.span}&direction=down&depth=8&limit=200`) as any;
    expect(apiDown.downstream_ids).toContain(state.trace.step);
    await expect(page.locator(`.jm-node[data-node-id="${state.trace.step}"].is-path`)).toBeVisible();
    await shot(page, 'x06-down-trace');
    // detail links keep identifiers
    const step2 = page.locator(`.jm-node[data-node-id="${state.trace.step}"]`);
    await step2.click();
    const flow = page.getByRole('link', { name: 'Flow에서 보기' });
    await expect(flow).toHaveAttribute('href', new RegExp(`run_id=${post.run_id}`));
    const learn = page.getByRole('link', { name: /규칙 학습/ }).first();
    const learnHref = await learn.getAttribute('href');
    note({ map_nodes: api.node_count, map_edges: api.edge_count, flow_href: await flow.getAttribute('href'), learning_href: learnHref });
    await page.keyboard.press('Escape');
    // list view keyboard (fresh load: only the stored relationships of the criteria, without merged path neighbours)
    await page.goto(`/judgment-map?rule_id=${encodeURIComponent(r2.ref)}`);
    await expect(page.getByTestId('jm-board')).toHaveAttribute('data-node-count', String(snap.rule2.node_count));
    await page.getByRole('button', { name: '목록 보기' }).click();
    const listIds: string[] = await page.locator('.jm-item').evaluateAll((els) => els.map((el) => (el as HTMLElement).dataset.nodeId as string));
    const apiRule = await get(ctx.request, `/api/graph/judgment?rule_id=${encodeURIComponent(r2.ref)}`) as any;
    expect(listIds.sort()).toEqual(apiRule.nodes.map((n: any) => n.id).sort());
    const first = page.locator('.jm-item[data-kind="ModelOutput"]').first();
    await first.focus();
    const startId = await first.getAttribute('data-node-id');
    await page.keyboard.press('ArrowRight');
    const focused = () => page.evaluate(() => (document.activeElement as HTMLElement).dataset.nodeId);
    await expect.poll(focused).not.toBe(startId);
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Enter');
    await expect(page.getByTestId('jm-detail').getByRole('heading', { level: 2 })).toBeVisible();
    await shot(page, 'x06-list-view');
    // Flow <-> Topology <-> Learning: same IDs
    await page.goto(`/observatory?request_id=${post.request_id}&run_id=${post.run_id}`);
    await page.getByRole('button', { name: /규칙 적용/ }).click();
    await expect(page.getByRole('dialog', { name: 'Trace 상세' })).toContainText(`실행 ${post.run_id}`);
    await expect(page.getByRole('link', { name: '같은 실행의 판단 맵 보기' })).toHaveAttribute('href', `/judgment-map?run_id=${post.run_id}`);
    await page.getByRole('button', { name: '업무 Topology' }).click();
    await expect(page.getByText('업무 Topology', { exact: true }).first()).toBeVisible();
    await page.goto(`/learning?rule_id=${encodeURIComponent(r2.ref)}`);
    await expect(page.getByRole('button', { name: new RegExp(r2.candidate) })).toHaveAttribute('aria-current', 'true');
    await expect(page.getByText(`버전 ${r2.ref} ·`)).toBeVisible();
    await shot(page, 'x06-learning-from-rule-id');
    await page.goto(`/judgment-map?rule_id=${encodeURIComponent(r2.ref)}`);
    await page.locator(`.jm-node[data-node-id="${r2.ref}"]`).click();
    const ruleLink = page.getByTestId('jm-detail').getByRole('link', { name: /규칙 학습/ });
    await expect(ruleLink).toHaveAttribute('href', new RegExp(`rule_id=${encodeURIComponent(r2.ref)}`));
    await ruleLink.click();
    await expect(page.getByRole('button', { name: new RegExp(r2.candidate) })).toHaveAttribute('aria-current', 'true');
    note({ rule_map: [snap.rule2.node_count, snap.rule2.edge_count] });
  });
});

test.describe(`[${phase}] map filters and zoom`, () => {
  test.skip(phase !== 'ui2', 'run once with ui2');
  test('[X06] criteria filters (request / rule / Config version / status), zoom controls — counts follow the graph API', async ({ browser, baseURL }) => {
    const ctx = await as(browser, baseURL as string, 'rule_admin');
    const page = await ctx.newPage();
    const form = page.getByRole('form', { name: '탐색 기준' });
    const out: Record<string, unknown> = {};
    for (const [label, field, value, query] of [['요청 ID', 'request_id', state.rule2.post_request.request_id, `request_id=${state.rule2.post_request.request_id}`],
                                                 ['규칙 ID', 'rule_id', state.rule2.ref, `rule_id=${encodeURIComponent(state.rule2.ref)}`],
                                                 ['Config 버전', 'config_version', String(state.pub_config), `config_version=${state.pub_config}`]] as const) {
      await page.goto('/judgment-map');
      await form.getByLabel(label).fill(value);
      await form.getByRole('button', { name: '적용' }).click();
      const api = await get(ctx.request, `/api/graph/judgment?${query}`) as any;
      await expect(page.getByTestId('jm-board')).toHaveAttribute('data-node-count', String(api.node_count));
      await expect(page.getByTestId('jm-board')).toHaveAttribute('data-edge-count', String(api.edge_count));
      await expect(page).toHaveURL(new RegExp(`${field}=`));
      out[field] = [api.node_count, api.edge_count];
    }
    await page.goto('/judgment-map');
    await form.getByLabel('상태').selectOption('published');
    await form.getByRole('button', { name: '적용' }).click();
    const byStatus = await get(ctx.request, '/api/graph/judgment?status=published') as any;
    await expect(page.getByTestId('jm-board')).toHaveAttribute('data-node-count', String(byStatus.node_count));
    out.status_published = [byStatus.node_count, byStatus.edge_count];
    const before = await page.getByTestId('jm-zoom-pct').innerText();
    await page.getByRole('button', { name: '확대' }).click();
    await expect(page.getByTestId('jm-zoom-pct')).not.toHaveText(before);
    await page.getByRole('button', { name: '축소' }).click();
    await page.getByRole('button', { name: '전체 보기' }).click();
    await shot(page, 'x06-filter-status');
    note(out);
  });
});

// ui2 = after stop / v2 / revert (before restart); ui3 = after browser reload + API/worker restart. Same assertions, fresh browser contexts.
test.describe(`[${phase}] lifecycle and persistence`, () => {
  test.skip(phase === 'ui1', 'ui2/ui3 only');

  test('[X07][X08] rule learning screen: lifecycle timeline, version states, application counts, validation card, observation = stored values (and after reload)', async ({ browser, baseURL }) => {
    test.setTimeout(120_000);
    const ctx = await as(browser, baseURL as string, 'rule_admin');
    const page = await ctx.newPage();
    const cfg = state.lifecycle.configs;
    const v1 = truth.rule_versions.find((v: any) => v.id === state.ref);
    const v2 = truth.rule_versions.find((v: any) => v.id === `${state.rule_id}@${state.lifecycle.v2.version}`);
    const check = async () => {
      await expect(page.getByRole('heading', { name: '규칙 학습', exact: true })).toBeVisible();
      await expect(page.getByRole('button', { name: new RegExp(candY) })).toHaveAttribute('aria-current', 'true');
      await page.getByLabel('규칙 버전').selectOption(String(v1.version));
      const tl = page.locator('.learning-timeline');
      for (const kind of ['후보 제안', '범위 수정 후 승인', '비교 검증', '게시 · 운영 중', '중단', '되돌리기']) await expect(tl).toContainText(kind);
      // every stored Config version where this rule's reference changed (publish / stop / v2 / revert) appears with its number
      const changed = truth.configs.filter((c: any, i: number) => {
        const mine = (x: any) => (x?.rules || []).filter((r: string) => r.startsWith(`${state.rule_id}@`));
        return JSON.stringify(mine(c)) !== JSON.stringify(i ? mine(truth.configs[i - 1]) : []);
      }).map((c: any) => c.version);
      expect(changed).toEqual(expect.arrayContaining([state.pub_config, cfg.stop, cfg.v2, cfg.revert]));
      for (const c of changed) await expect(tl).toContainText(`Config v${c}`);
      // version selector: both stored versions; counts equal the stored APPLIED rows per version
      const select = page.getByLabel('규칙 버전');
      for (const v of [v1, v2]) {
        await select.selectOption(String(v.version));
        await expect(page.getByText(`버전 ${v.id} ·`)).toContainText(`적용 기록 ${v.applications}`);
        await expect(page.getByText(`버전 ${v.id} ·`)).toContainText(`게시 Config ${v.configs.sort((a: number, b: number) => a - b).map((c: number) => `v${c}`).join(', ')}`);
      }
      await select.selectOption(String(v1.version));
      const val = truth.validations.find((x: any) => x.id === state.validation_id);
      const card = page.getByRole('region', { name: '비교 검증' });
      await expect(card.locator('h3 .mono')).toHaveText(val.id);
      await expect(card).toContainText(`표본 ${val.sample_count}건 · 사람 확정 정답 ${val.labeled_count}건`);
      await expect(card).toContainText(`부작용 ${val.side_effects}건`);
      const db = truth.effects[state.rule_id];
      await expect(page.getByTestId('used-count')).toHaveText(String(db.used.sample_count));
      await expect(page.getByTestId('out-count')).toHaveText(String(db.out_of_scope.sample_count));
      await expect(page.getByTestId('effect-verdict')).toHaveText('관찰 중 · 표본 부족');
    };
    await page.goto(`/learning?candidate_id=${candY}`);
    await check();
    await shot(page, 'x07-timeline-after-lifecycle');
    await page.reload();
    await check();
    await shot(page, 'x08-after-reload');
    // support rows still present and identical
    const table = page.getByRole('table', { name: '근거 수정 기록' });
    for (const c of supportCorrections) await expect(table.getByRole('row').filter({ hasText: c.request_id })).toContainText(`${c.revision_id} · ${c.run_id} · v${c.config_version}`);
    note({ changed_config_versions: truth.configs.length, v1: { applications: v1.applications, configs: v1.configs }, v2: { applications: v2.applications, configs: v2.configs }, configs: cfg, timeline: await page.locator('.learning-timeline').innerText() });
  });

  test('[X08] judgment map and trace: counts and IDs equal the stored snapshot after reload', async ({ browser, baseURL }) => {
    test.setTimeout(120_000);
    const ctx = await as(browser, baseURL as string, 'rule_admin');
    const page = await ctx.newPage();
    const snap = JSON.parse(readFileSync(`${OUT}/snap.${process.env.X38_SNAP || 'pre'}.json`, 'utf8')).api.graph;
    const r2 = state.rule2;
    for (const [name, query] of [['request', `request_id=${r2.post_request.request_id}`], ['rule2', `rule_id=${encodeURIComponent(r2.ref)}`], ['rule_ai_need', `rule_id=${encodeURIComponent(state.ref)}`]] as const) {
      await page.goto(`/judgment-map?${query}`);
      await page.reload();
      const board = page.getByTestId('jm-board');
      await expect(board).toHaveAttribute('data-node-count', String(snap[name].node_count));
      await expect(board).toHaveAttribute('data-edge-count', String(snap[name].edge_count));
      const ids: string[] = await page.locator('.jm-node:not(.is-group)').evaluateAll((els) => els.map((el) => (el as HTMLElement).dataset.nodeId as string));
      for (const id of ids) expect(snap[name].nodes).toContain(id);
    }
    // step -> source span still traceable
    await page.goto(`/judgment-map?request_id=${r2.post_request.request_id}`);
    await page.locator(`.jm-node[data-node-id="${state.trace.step}"]`).click();
    await expect(page.locator('.jm-node[data-kind="EvidenceSpan"].is-path').first()).toBeVisible();
    await shot(page, 'x08-map-trace');
    // Trace of the stored run
    await page.goto(`/observatory?request_id=${r2.post_request.request_id}&run_id=${r2.post_request.run_id}`);
    await page.getByRole('button', { name: /규칙 적용/ }).click();
    await expect(page.getByRole('dialog', { name: 'Trace 상세' })).toContainText(`실행 ${r2.post_request.run_id}`);
    note({ checked: Object.fromEntries(Object.entries(snap).map(([k, v]: any) => [k, [v.node_count, v.edge_count]])) });
  });
});
