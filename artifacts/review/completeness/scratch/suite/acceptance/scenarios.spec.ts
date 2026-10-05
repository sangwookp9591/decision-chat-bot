import { expect, test } from '@playwright/test';
import { actor, outDir, pendingReview, shot, submitApi, visibleTotals, waitJudged, tenant, type Actor } from './helpers';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

/**
 * T21 UI acceptance (live Jev, real Neo4j, dedicated tenant): scenarios 1-8 through the real UI with
 * every displayed value compared with the stored value read through the API. Labels are never asserted
 * as ground truth. Run: make test-acceptance-ui (see Makefile) or the command in playwright.acceptance.config.ts.
 */
test.describe.configure({ mode: 'serial' });
test.setTimeout(600_000);

const evidence: Record<string, unknown> = {};
let base = '';
let rq: Actor, rv: Actor, op: Actor, failedActor: Actor;
let failedId = '';
const keep = (k: string, v: unknown) => { evidence[k] = v; writeFileSync(join(outDir, 'ui-evidence.json'), JSON.stringify(evidence, null, 2)); };

test.beforeAll(async ({ browser }, info) => {
  base = info.project.use.baseURL as string;
  rq = await actor(browser, base, 'requester');
  rv = await actor(browser, base, 'reviewer');
  op = await actor(browser, base, 'operator');
  // t-acc21f is served by a worker with a deliberately invalid Jev key: Jev rejects it (real failed run).
  // Submitted first so the retry budget elapses while the other scenarios run.
  failedActor = await actor(browser, base, 'requester', `${tenant}f`);
  failedId = await submitApi(failedActor, '월별 판매 현황을 조회하는 화면이 필요합니다.');
});

// The provisional card also has a 판단 결과 heading; only the saved result (not .provisional-result) proves the judgment is stored.
const finalResult = (page: import('@playwright/test').Page) => page.locator('.result-stack:not(.provisional-result)').getByRole('heading', { name: '판단 결과', exact: true });

const CLASS_LABELS: Record<string, string> = { ai_need: 'AI 필요성', feasibility: '개발 가능성', urgency: '긴급도', lead_org: '주관 조직' };

async function uiClassifications(page: import('@playwright/test').Page) {
  const out: Record<string, string> = {};
  for (const [key, label] of Object.entries(CLASS_LABELS)) {
    const card = page.locator('.judgment-card', { has: page.getByRole('heading', { name: label, exact: true }) });
    const uncertain = card.locator('.uncertain-result span');
    out[key] = (await uncertain.count()) ? (await uncertain.first().innerText()).trim() : (await card.locator('.scale-options .selected').first().innerText()).trim();
  }
  return out;
}

async function submitViaUi(a: Actor, text: string, files: { name: string; mimeType: string; buffer: Buffer }[] = []) {
  await a.page.goto('/');
  await a.page.getByLabel('요청 내용').fill(text);
  if (files.length) await a.page.getByLabel('파일 첨부').setInputFiles(files);
  const [resp] = await Promise.all([
    a.page.waitForResponse((r) => r.url().endsWith('/api/requests') && r.request().method() === 'POST'),
    a.page.getByRole('button', { name: '요청 보내기' }).click(),
  ]);
  expect(resp.status()).toBe(202);
  return (await resp.json()).request_id as string;
}

let s1: string, s2: string, s3: string, s4: string, s6: string;
function recall(key: string): string {
  try { return JSON.parse(readFileSync(join(outDir, 'ui-evidence.json'), 'utf8'))[key]?.request_id || ''; } catch { return ''; }
}

test('S1 general technical request: UI result equals stored judgment', async () => {
  s1 = await submitViaUi(rq, 'SAP에서 내려받은 매출 CSV를 월별로 집계해 화면에 보여 주세요.');
  await expect(finalResult(rq.page)).toBeVisible({ timeout: 200_000 });
  await expect(rq.page.locator('.environment-badge.mode-live').last()).toBeVisible();
  const api = await (await rq.api.get(`/api/requests/${s1}/judgment`)).json();
  const ui = await uiClassifications(rq.page);
  expect(ui).toEqual(Object.fromEntries(Object.keys(CLASS_LABELS).map((k) => [k, api.classifications[k]])));
  await expect(rq.page.locator('main')).toContainText(api.run_id);
  for (const t of api.draft_tasks) await expect(rq.page.locator('.task-row', { hasText: t.title }).first()).toBeVisible();
  await shot(rq.page, 's1-general-technical');
  keep('s1', { request_id: s1, run_id: api.run_id, ui });
});

test('S2 mixed request: reviewer approves in UI; stored tasks, lead/collab and predecessors show in 업무', async () => {
  const text = '고객 문의 메일을 자동 분류하고 답변 초안을 생성하는 생성형 AI 기능이 필요합니다. 모델 평가 방법, 사내 시스템 연동, 현업의 승인 기준이 필요합니다.';
  let id = '', j: Record<string, any> = {};
  for (let i = 0; i < 4; i++) {
    id = await submitApi(rq, text);
    j = await waitJudged(rq, id);
    const methods = new Set(j.draft_tasks.map((t: any) => t.method));
    if (methods.has('AI') && methods.size >= 2) break;
  }
  expect(new Set(j.draft_tasks.map((t: any) => t.method)).has('AI')).toBeTruthy();
  s2 = id;
  const row = await pendingReview(rv, id);
  await rv.page.goto('/review');
  await rv.page.locator('nav[aria-label="검토 대기 목록"] button', { hasText: id }).click();
  await expect(rv.page.getByRole('heading', { name: 'AI 원안과 검토 값' })).toBeVisible();
  await shot(rv.page, 's2-review-before-approve');
  await rv.page.getByRole('button', { name: '승인', exact: true }).click();
  await expect(rv.page.getByRole('status')).toBeVisible();
  const tasks = (await (await rv.api.get(`/api/tasks?request_id=${id}`)).json()).tasks as any[];
  expect(tasks.length).toBe(j.draft_tasks.length);
  await rv.page.goto('/tasks');
  for (const t of tasks) await expect(rv.page.locator('main')).toContainText(t.title);
  await shot(rv.page, 's2-tasks-after-approval');
  keep('s2', { request_id: id, review_id: row.id, tasks: tasks.map((t) => ({ id: t.id, title: t.title, method: t.method, lead: t.lead_org, collab: t.collab_orgs, pred: t.predecessors, status: t.status })) });
});

test('S3 urgent request: reasons, review and priority on screen', async () => {
  const texts = ['오늘 오후 6시까지 마감해야 하는 월말 정산 시스템이 멈춰서 전 부서 업무가 중단됐습니다. 당일 마감 전에 반드시 복구가 필요합니다.',
    '주문 접수 시스템이 중단되어 모든 영업 업무가 멈췄습니다. 오늘 안에 마감해야 하는 고객 계약이 있어 즉시 처리가 필요합니다.'];
  let id = '', j: Record<string, any> = {};
  for (let i = 0; i < 4; i++) {
    id = await submitApi(rq, texts[i % 2]);
    j = await waitJudged(rq, id);
    if (j.classifications.urgency === '긴급') break;
  }
  expect(j.classifications.urgency).toBe('긴급');
  s3 = id;
  const normal = await submitApi(rq, '사내 공지사항 게시판의 글꼴 크기를 조금 키워 주세요.');
  await waitJudged(rq, normal);
  await pendingReview(rv, normal);
  await rv.page.goto('/review');
  const list = rv.page.locator('nav[aria-label="검토 대기 목록"]');
  await expect(list.locator('button', { hasText: id })).toBeVisible();
  const box = list.getByLabel('긴급 우선 정렬');
  if (!(await box.isChecked())) await box.check();
  await expect(list.locator('button').first()).toContainText('긴급');
  await list.locator('button', { hasText: id }).click();
  await expect(rv.page.locator('main')).toContainText('필수 검토');
  await shot(rv.page, 's3-urgent-review-priority');
  keep('s3', { request_id: id, run_id: j.run_id, reasons: j.review_reasons });
});

test('S4 insufficient information: reasons shown, request-info keeps everything unexecuted', async () => {
  s4 = await submitApi(rq, '고객 개인 데이터를 외부 시스템과 연동해 자동 분석하고 싶은데, 어떤 데이터가 있는지, 접근 권한과 승인이 있는지 아직 아무도 모릅니다.');
  const j = await waitJudged(rq, s4);
  await pendingReview(rv, s4);
  await rq.page.goto('/');
  await rq.page.getByText(s4).first().click();
  await expect(finalResult(rq.page)).toBeVisible();
  await expect(rq.page.locator('main')).toContainText('검토 사유');
  for (const reason of j.review_reasons.slice(0, 2)) await expect(rq.page.locator('main')).toContainText(reason);
  await shot(rq.page, 's4-insufficient-information');
  await rv.page.goto('/review');
  await rv.page.locator('nav[aria-label="검토 대기 목록"] button', { hasText: s4 }).click();
  await rv.page.getByLabel('결정 사유').fill('데이터 목록과 접근 승인 문서를 보완해 주세요');
  await rv.page.getByRole('button', { name: '정보 요청' }).click();
  await expect(rv.page.getByRole('status')).toBeVisible();
  expect((await (await rv.api.get(`/api/tasks?request_id=${s4}`)).json()).tasks).toHaveLength(0);
  const d = await (await rq.api.get(`/api/requests/${s4}`)).json();
  expect(d.request.status).toBe('보완 필요');
  await rq.page.goto('/');
  await expect(rq.page.locator('main')).toContainText('보완 필요');
  await shot(rq.page, 's4-after-request-info');
  keep('s4', { request_id: s4, status: d.request.status, reasons: j.review_reasons });
});

test('S5 documents: PDF+DOCX+MD plus a damaged file; explicit exclusion; per-file evidence', async () => {
  const fx = (n: string) => readFileSync(join(process.cwd(), '..', 'backend', 'tests', 'acceptance', 'fixtures', n));
  const files = [
    { name: 'returns.pdf', mimeType: 'application/pdf', buffer: fx('returns.pdf') },
    { name: 'approval.docx', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', buffer: fx('approval.docx') },
    { name: 'rooms.md', mimeType: 'text/markdown', buffer: fx('rooms.md') },
    { name: 'broken.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.7 this is not a valid pdf') },
  ];
  const id = await submitViaUi(rq, '세 문서의 요청 내용을 함께 검토해 주세요.', files);
  const exclude = rq.page.getByRole('button', { name: '제외하고 진행' });
  await expect(exclude).toBeVisible({ timeout: 30_000 });
  await expect(rq.page.locator('main')).toContainText('broken.pdf');
  await shot(rq.page, 's5-damaged-file-needs-decision');
  const before = await (await rq.api.get(`/api/requests/${id}`)).json();
  expect(before.request.status).toBe('needs_file_decision');
  await exclude.click();
  await expect(finalResult(rq.page)).toBeVisible({ timeout: 200_000 });
  const d = await (await rq.api.get(`/api/requests/${id}`)).json();
  expect(d.attachments.filter((a: any) => a.excluded).map((a: any) => a.filename)).toEqual(['broken.pdf']);
  await expect(rq.page.getByText(/revision/).first()).toBeVisible();
  const evidenceButtons = rq.page.getByRole('button', { name: /근거 열기/ });
  const n = await evidenceButtons.count();
  if (n) { await evidenceButtons.first().click(); await expect(rq.page.getByRole('heading', { name: '근거 원문' })).toBeVisible(); }
  await shot(rq.page, 's5-after-exclusion');
  keep('s5', { request_id: id, revision: d.request.revision_number, excluded: ['broken.pdf'], evidence_buttons: n });
});

test('S6 human intervention: modify-approve preserves original; reject and request-info are separate', async () => {
  s6 = await submitApi(rq, '분기별 시설 점검 일정을 부서별로 조회하는 화면이 필요합니다.');
  const j = await waitJudged(rq, s6);
  const row = await pendingReview(rv, s6);
  await rv.page.goto('/review');
  await rv.page.locator('nav[aria-label="검토 대기 목록"] button', { hasText: s6 }).click();
  await rv.page.getByLabel('개발 가능성 수정').fill('가능');
  await rv.page.getByLabel('결정 사유').fill('검토자가 데이터와 권한이 있음을 확인함');
  await rv.page.getByRole('button', { name: '수정 승인' }).click();
  await expect(rv.page.getByRole('status')).toBeVisible();
  const after = await (await rv.api.get(`/api/reviews/${row.id}`)).json();
  expect(after.final_classifications.feasibility).toBe('가능');
  const original = (await (await rv.api.get(`/api/requests/${s6}/judgment`)).json()).classifications;
  expect(original).toEqual(j.classifications);
  const corr = after.history.flatMap((h: any) => h.corrections).find((c: any) => c.field === 'feasibility');
  expect(corr.ai_value).toBe(j.classifications.feasibility);
  expect(corr.corrected_value).toBe('가능');
  await rv.page.locator('nav[aria-label="검토 대기 목록"]').waitFor({ state: 'attached' });
  await shot(rv.page, 's6-modify-approved');
  // reject and request-info on separate requests
  const outcomes: Record<string, string> = {};
  for (const [action, text, label] of [['reject', '사내 프린터 위치 안내 페이지를 만들어 주세요.', '반려'], ['request_info', '사내 휴게실 예약 알림 기능을 추가해 주세요.', '정보 요청']] as const) {
    const id = await submitApi(rq, text);
    await waitJudged(rq, id);
    await pendingReview(rv, id);
    await rv.page.goto('/review');
    await rv.page.locator('nav[aria-label="검토 대기 목록"] button', { hasText: id }).click();
    await rv.page.getByLabel('결정 사유').fill(action === 'reject' ? '현재 우선순위에 없는 요청입니다' : '예약 대상 시설 목록이 필요합니다');
    await rv.page.getByRole('button', { name: label, exact: true }).click();
    await expect(rv.page.getByRole('status')).toBeVisible();
    outcomes[action] = (await (await rq.api.get(`/api/requests/${id}`)).json()).request.status;
    expect((await (await rv.api.get(`/api/tasks?request_id=${id}`)).json()).tasks).toHaveLength(0);
  }
  expect(outcomes).toEqual({ reject: '반려', request_info: '보완 필요' });
  keep('s6', { request_id: s6, review_id: row.id, original, final: after.final_classifications, others: outcomes });
});

test('S7 re-analysis from the UI: previous/new runs distinguished, no duplicate tasks', async () => {
  const before = await (await rv.api.get(`/api/tasks?request_id=${s2}`)).json();
  rq.page.once('dialog', (d) => void d.accept());
  await rq.page.goto('/');
  await rq.page.getByText(s2).first().click();
  await expect(finalResult(rq.page)).toBeVisible();
  await rq.page.getByRole('button', { name: '다시 분석', exact: true }).click();
  await expect.poll(async () => (await (await rq.api.get(`/api/requests/${s2}/runs`)).json()).runs.length, { timeout: 60_000 }).toBe(2);
  await expect.poll(async () => {
    const runs = (await (await rq.api.get(`/api/requests/${s2}/runs`)).json()).runs as any[];
    return runs.every((r) => ['judgment_saved', 'failed'].includes(r.status));
  }, { timeout: 200_000, intervals: [3000] }).toBe(true);
  await rq.page.reload();
  await rq.page.getByText(s2).first().click();
  await expect(rq.page.getByRole('heading', { name: '이전 실행 비교' })).toBeVisible({ timeout: 60_000 });
  const after = await (await rv.api.get(`/api/tasks?request_id=${s2}`)).json();
  expect(after.tasks.map((t: any) => t.id).sort()).toEqual(before.tasks.map((t: any) => t.id).sort());
  await shot(rq.page, 's7-reanalysis-comparison');
  keep('s7', { request_id: s2, tasks_unchanged: after.tasks.length });
});

test('S8 observe and replay: success, waiting-for-review and failed runs; Play changes nothing', async ({ browser }) => {
  await expect.poll(async () => (await (await failedActor.api.get(`/api/requests/${failedId}`)).json()).request.status, { timeout: 300_000, intervals: [5000] }).toMatch(/failed|실패/);
  const cases: [string, Actor, string][] = [['success', op, s2 || recall('s2')], ['waiting', op, s3 || recall('s3')], ['failed', failedActor, failedId]];
  const labels: Record<string, string> = { succeeded: '성공', failed: '실패', skipped: '건너뜀', waiting_human: '사람 검토', running: '진행 중', pending: '대기' };
  const result: Record<string, unknown> = {};
  for (const [name, who, rid] of cases) {
    const runs = await (await who.api.get(`/api/requests/${rid}/runs`)).json();
    const runId = runs.active_run_id || runs.runs[0].id;
    const flow = await (await who.api.get(`/api/observe/runs/${runId}/flow`)).json();
    await who.page.goto(`/observatory?request_id=${rid}&run_id=${runId}`);
    await expect(who.page.locator('.obs-node').first()).toBeVisible({ timeout: 30_000 });
    expect(await who.page.locator('.obs-node').count()).toBe(flow.nodes.length);
    const shown = await who.page.locator('.obs-node').allInnerTexts();
    flow.nodes.forEach((n: any, i: number) => {
      expect(shown[i]).toContain(labels[n.status] || n.status);
      expect(shown[i]).toContain(n.name || n.kind);
    });
    const totalsBefore = await visibleTotals(who);
    await who.page.getByRole('button', { name: '재생' }).click();
    await who.page.waitForTimeout(1500);
    const pause = who.page.getByRole('button', { name: /일시정지/ });
    if (await pause.count()) await pause.click();  // a failed run stops playback by itself
    await who.page.getByRole('button', { name: '전체 결과' }).click();
    const afterNodes = await who.page.locator('.obs-node').allInnerTexts();
    flow.nodes.forEach((n: any, i: number) => expect(afterNodes[i]).toContain(labels[n.status] || n.status));
    expect(await visibleTotals(who)).toEqual(totalsBefore);
    await shot(who.page, `s8-observatory-${name}`);
    result[name] = { request_id: rid, run_id: runId, nodes: flow.nodes.map((n: any) => `${n.name || n.kind}:${n.status}`), totals_unchanged: totalsBefore };
  }
  keep('s8', result);
});

test('S9 script/HTML in a document is shown as inert text (no dialog, no execution) for requester and reviewer', async ({ browser }) => {
  const payload = '<script>window.__acc_xss=1</script><img src=x onerror="window.__acc_xss=2;alert(1)"> 회의실 예약 화면 요청';
  const dialogs: string[] = [];
  for (const a of [rq, rv]) a.page.on('dialog', (d) => { dialogs.push(d.message()); void d.dismiss(); });
  const id = await submitViaUi(rq, payload, [{ name: 'script.md', mimeType: 'text/markdown', buffer: Buffer.from(payload) }]);
  await expect(finalResult(rq.page)).toBeVisible({ timeout: 200_000 });
  await expect(rq.page.locator('main')).toContainText('<script>');
  await pendingReview(rv, id);
  await rv.page.goto('/review');
  await rv.page.locator('nav[aria-label="검토 대기 목록"] button', { hasText: id }).click();
  await expect(rv.page.locator('main')).toContainText('<script>');
  for (const a of [rq, rv]) {
    expect(await a.page.evaluate(() => (window as unknown as { __acc_xss?: number }).__acc_xss)).toBeUndefined();
    expect(await a.page.locator('main img[src="x"]').count()).toBe(0);
  }
  expect(dialogs).toEqual([]);
  await shot(rv.page, 's9-script-text-inert');
  keep('s9', { request_id: id, dialogs: dialogs.length });
});

test('G10 WebMCP product tools: unauthorised IDs return API 404 through the tool handlers; unsupported browsers still work', async ({ browser }) => {
  // NOTE: the shim below only *captures* what the product registers. It is not a browser agent and is
  // not evidence for G10 "real browser agent invocation" (stays blocked; see gate-evidence.md).
  const other = await actor(browser, base, 'requester', `${tenant}b`);
  await other.page.addInitScript(() => {
    const w = window as unknown as { __tools: Record<string, { execute: (i: unknown) => Promise<unknown> }> };
    w.__tools = {};
    (document as unknown as { modelContext: unknown }).modelContext = { registerTool: async (t: { name: string; execute: (i: unknown) => Promise<unknown> }) => { w.__tools[t.name] = t; } };
  });
  await other.page.goto('/');
  await expect.poll(() => other.page.evaluate(() => Object.keys((window as unknown as { __tools: object }).__tools).sort().join(',')), { timeout: 15_000 }).toBe('get_request,get_trace,search_requests');
  const foreignRequest = s2 || recall('s2');
  const foreignRun = (await (await rq.api.get(`/api/requests/${foreignRequest}/runs`)).json()).active_run_id as string;
  const call = (name: string, input: unknown) => other.page.evaluate(async ([n, i]) => {
    const tools = (window as unknown as { __tools: Record<string, { execute: (x: unknown) => Promise<unknown> }> }).__tools;
    try { return { ok: true, value: await tools[n as string].execute(i) }; } catch (e) { return { ok: false, message: String((e as Error).message) }; }
  }, [name, input] as [string, unknown]);
  const gotRequest = await call('get_request', { request_id: foreignRequest });
  const gotTrace = await call('get_trace', { run_id: foreignRun });
  expect(gotRequest).toMatchObject({ ok: false });
  expect((gotRequest as { message: string }).message).toContain('API_ERROR 404');
  expect((gotTrace as { message: string }).message).toContain('API_ERROR 404');
  const search = await call('search_requests', { limit: 100 }) as { ok: boolean; value: { items: { id: string }[] } };
  expect(search.ok).toBe(true);
  expect(search.value.items.map((x) => x.id)).not.toContain(foreignRequest);
  // own-tenant data stays reachable through the same tools
  const ownId = await submitApi(other, '내 테넌트 요청: 월별 재고 조회 화면이 필요합니다.');
  const own = await call('get_request', { request_id: ownId }) as { ok: boolean; value: { id: string } };
  expect(own.ok).toBe(true);
  expect(own.value.id).toBe(ownId);
  // browsers without WebMCP: the page is usable (no tools, no crash)
  const plain = await actor(browser, base, 'requester');
  await plain.page.goto('/');
  await expect(plain.page.getByRole('heading', { name: '일동이와 요청 접수' })).toBeVisible();
  expect(await plain.page.evaluate(() => 'modelContext' in document)).toBe(false);
  keep('g10_handlers', { foreign_request: foreignRequest, get_request: (gotRequest as { message: string }).message.slice(0, 80), get_trace: (gotTrace as { message: string }).message.slice(0, 80), own_request_ok: ownId, real_browser_agent_invocation: 'not performed (blocked)' });
});
