import { execFileSync, spawn, type ChildProcess } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { expect, test, type APIRequestContext, type Browser } from '@playwright/test';

/**
 * 규칙 학습 실데이터 E2E (live Jev, 실제 Neo4j). 검토자 수정 3건 → 후보 → 규칙 관리자 승인(범위 확정)
 * → 검증 → 게시 → 새 요청의 '범위 안 사용' 증가 → 중단.
 *
 * 준비: E2E 전용 tenant를 새로 만들어(실행마다 새 tenant — 후보 ID가 범위로 결정되므로) 그 tenant만 처리하는 worker를 띄운다.
 *   E2E_TENANT=<tenant> E2E_API=http://127.0.0.1:<port> E2E_PORT=<port> npx playwright test -c playwright.learning.config.ts
 * 계정은 `<role>@<tenant>.dev` / JEVTRIAGE_DEV_PASSWORD(기본 dev-only-change-me).
 */
const tenant = `${process.env.E2E_TENANT || 't-alpha'}-learning-${randomUUID().slice(0, 8)}`;
let worker: ChildProcess;
test.beforeAll(() => {
  execFileSync('../backend/.venv/bin/python', ['../backend/tests/acceptance/provision.py', tenant]);
  if (process.env.JEV_MODE === 'mock') worker = spawn('../backend/.venv/bin/python', ['../scripts/e2e/mock_worker.py', '--tenant', tenant], { stdio: 'ignore' });
  else throw new Error('Learning fixture needs mock mode; live learning requires a dedicated provisioned worker.');
});
test.afterAll(async () => {
  if (worker && worker.exitCode === null) {
    const closed = new Promise<void>(resolve => worker.once('exit', () => resolve()));
    worker.kill('SIGTERM'); await closed;
  }
});
const password = process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me';
type Review = { id: string; request_id: string };

async function login(api: APIRequestContext, role: string) {
  const response = await api.post('/api/auth/login', { data: { email: `${role}@${tenant}.dev`, password } });
  expect(response.ok(), `login ${role} failed: ${response.status()}`).toBeTruthy();
  return (await api.storageState()).cookies.find((cookie) => cookie.name === 'jev_csrf')?.value || '';
}
async function submit(api: APIRequestContext, csrf: string, label: string) {
  const response = await api.post('/api/requests', {
    headers: { 'Idempotency-Key': crypto.randomUUID(), 'X-CSRF-Token': csrf },
    multipart: {
      text: `사내 회의실 예약 현황을 부서별로 조회하고 예약 가능 시간을 확인하는 화면이 필요합니다. (${label})`,
      files: { name: 'rooms.md', mimeType: 'text/markdown', buffer: Buffer.from('회의실 예약 현황을 부서별로 조회합니다. 예약 가능 시간과 담당 부서를 확인할 수 있어야 합니다.') },
    },
  });
  expect(response.ok(), `submit failed: ${response.status()}`).toBeTruthy();
  const body = await response.json() as { request_id?: string; id?: string };
  return (body.request_id || body.id) as string;
}
async function pendingReviews(api: APIRequestContext, requestIds: string[]) {
  let found: Review[] = [];
  await expect.poll(async () => {
    const list = await (await api.get('/api/reviews?status=pending')).json() as { reviews: Review[] };
    found = list.reviews.filter((row) => requestIds.includes(row.request_id));
    return found.length;
  }, { timeout: 240_000, intervals: [3000], message: 'live judgments did not produce reviews' }).toBe(requestIds.length);
  return found;
}
async function context(browser: Browser, baseURL: string, role: string) {
  const ctx = await browser.newContext({ baseURL });
  await login(ctx.request, role);
  return ctx;
}

test('reviewer corrections become a candidate; rule admin approves, validates, publishes, observes use, then stops', async ({ browser, baseURL }) => {
  test.setTimeout(900_000);
  const base = baseURL as string;
  const requester = (await browser.newContext({ baseURL: base })).request;
  // Log in once: concurrent first logins for one account race on the LoginAttempt MERGE in the auth router.
  const requesterCsrf = await login(requester, 'requester');

  // 1. Four live requests; three with the same AI original for ai_need get the same reviewer correction.
  const ids = await Promise.all(['A', 'B', 'C', 'D'].map((label) => submit(requester, requesterCsrf, label)));
  const reviewer = await context(browser, base, 'reviewer');
  const csrf = (await reviewer.request.storageState()).cookies.find((c) => c.name === 'jev_csrf')?.value || '';
  const reviews = await pendingReviews(reviewer.request, ids);
  const details = await Promise.all(reviews.map(async (r) => (await (await reviewer.request.get(`/api/reviews/${r.id}`)).json()) as { review: Record<string, any>; final_classifications: Record<string, string> }));
  const groups = new Map<string, typeof details>();
  for (const d of details) groups.set(d.final_classifications.ai_need, [...(groups.get(d.final_classifications.ai_need) || []), d]);
  const [original, same] = [...groups.entries()].sort((a, b) => b[1].length - a[1].length)[0];
  expect(same.length, `live Jev gave differing ai_need originals: ${JSON.stringify([...groups].map(([k, v]) => [k, v.length]))}`).toBeGreaterThanOrEqual(3);
  const corrected = ['필요', '불필요', '혼합'].find((value) => value !== original) as string;
  const correctedRequests: string[] = [];
  for (const d of same.slice(0, 3)) {
    const decided = await reviewer.request.post(`/api/reviews/${d.review.id}/decision`, {
      headers: { 'Idempotency-Key': crypto.randomUUID(), 'X-CSRF-Token': csrf },
      data: { action: 'approve_with_changes', request_id: d.review.request_id, input_revision: d.review.revision_id, run_id: d.review.run_id, draft_version: d.review.draft_version, review_version: d.review.review_version, changes: { classifications: { ai_need: corrected } }, reason: '규칙 학습 E2E: AI 필요성 수정' },
    });
    expect(decided.ok(), `decision failed: ${decided.status()} ${await decided.text()}`).toBeTruthy();
    correctedRequests.push(d.review.request_id);
  }

  // 2. Reviewer: facts are counted, candidate generated, every administrator action is disabled with a reason.
  const reviewerPage = await reviewer.newPage();
  await reviewerPage.goto('/learning');
  await expect(reviewerPage.getByRole('heading', { name: '규칙 학습', exact: true })).toBeVisible();
  await expect(reviewerPage.getByText('모델 재학습 없음 · 규칙·컨텍스트로만 반영')).toBeVisible();
  const stored = await (await reviewer.request.get('/api/learning/corrections?field=ai_need')).json() as { corrections: Array<{ id: string; request_id: string }> };
  expect(stored.corrections.length).toBeGreaterThanOrEqual(3);
  await expect(reviewerPage.getByText(`수정 기록 ${(await (await reviewer.request.get('/api/learning/corrections')).json() as { corrections: unknown[] }).corrections.length}건`)).toBeVisible();
  await reviewerPage.getByRole('button', { name: '수정 기록에서 후보 집계' }).click();
  await expect(reviewerPage.getByRole('status')).toContainText('후보를 다시 집계했습니다');
  const listed = await (await reviewer.request.get('/api/learning/candidates')).json() as { candidates: Array<{ id: string; field: string; status: string; support_count: number }> };
  const candidate = listed.candidates.find((c) => c.field === 'ai_need' && c.support_count >= 3);
  expect(candidate, 'no ai_need candidate with >=3 support').toBeTruthy();
  await reviewerPage.getByRole('button', { name: new RegExp(candidate!.id) }).click();
  const table = reviewerPage.getByRole('table', { name: '근거 수정 기록' });
  for (const requestId of correctedRequests) await expect(table.getByText(requestId)).toBeVisible();
  await expect(table.getByText('지지').first()).toBeVisible();
  await expect(reviewerPage.getByRole('button', { name: '승인', exact: true })).toBeDisabled();
  await expect(reviewerPage.getByText('규칙 관리자만 실행할 수 있습니다.').first()).toBeVisible();
  await expect(reviewerPage.getByText('요청 한 건의 수정 승인은 규칙 게시가 아닙니다.')).toBeVisible();

  // 3. Rule admin: scope-changed approval (empty scope = every request in this E2E tenant).
  const admin = await context(browser, base, 'rule_admin');
  const page = await admin.newPage();
  await page.goto('/learning');
  await page.getByRole('button', { name: new RegExp(candidate!.id) }).click();
  await expect(page.getByText('적용 범위 (제안)')).toBeVisible();
  await page.getByLabel('결정 사유').fill('E2E: 범위를 모든 요청으로 확정');
  await page.getByLabel('확정 범위').fill('{"all": []}');
  await page.getByRole('button', { name: '범위 수정 후 승인' }).click();
  await expect(page.getByRole('status')).toContainText('범위를 수정해 승인하고');
  await expect(page.getByText('적용 범위 (확정)')).toBeVisible();
  await expect(page.getByText('조건 없음 (모든 요청)').first()).toBeVisible();
  await expect(page.getByRole('button', { name: '게시', exact: true })).toBeDisabled();
  await expect(page.getByText('검증을 완료하지 않은 규칙은 게시할 수 없습니다.')).toBeVisible();

  // 4. Shadow validation (no side effects), mark validated, publish.
  await page.getByRole('button', { name: '검증 실행' }).click();
  await expect(page.getByRole('status')).toContainText('비교 검증을 실행했습니다');
  const card = page.getByRole('region', { name: '비교 검증' });
  await expect(card).toContainText('부작용 0건');
  await expect(card).toContainText('확정이 아닙니다');
  await expect(card).toContainText(/사람 확정 정답 \d+건/);
  const validationId = await card.locator('h3 .mono').innerText();
  await page.reload();
  await expect(page.getByRole('region', { name: '비교 검증' }).locator('h3')).toContainText(validationId);
  await page.getByLabel('결정 사유').fill('E2E: 부작용 0건 확인');
  await page.getByRole('button', { name: '검증 완료 처리' }).click();
  await expect(page.getByRole('status')).toContainText('검증 완료로 표시');
  await page.getByLabel('결정 사유').fill('E2E: 게시');
  await page.getByRole('button', { name: '게시', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('새 Config 버전으로 게시했습니다');
  await expect(page.getByText(/상태 게시 · 운영 중/)).toBeVisible();
  const active = await (await admin.request.get('/api/policy/active')).json() as { version: number; config: { rules: Array<{ rule_id: string }> } };
  expect(active.config.rules.length).toBe(1);
  const ruleId = active.config.rules[0].rule_id;

  // 5. A new request started after publication is processed under the new Config; "범위 안 사용" rises.
  const fresh = await submit(requester, requesterCsrf, 'after-publish');
  await pendingReviews(reviewer.request, [fresh]);
  let apiUsed = 0;
  await expect.poll(async () => {
    await page.getByRole('button', { name: '새로고침' }).click();
    const effects = await (await admin.request.get(`/api/learning/rules/${ruleId}/effects`)).json() as { groups: { used: { sample_count: number } } };
    apiUsed = effects.groups.used.sample_count;
    return apiUsed;
  }, { timeout: 60_000, intervals: [2000] }).toBeGreaterThanOrEqual(1);
  await expect(page.getByTestId('used-count')).toHaveText(String(apiUsed));
  await expect(page.getByTestId('effect-verdict')).toHaveText('관찰 중 · 표본 부족');
  await expect(page.getByText(/표본 부족: \d+건 \/ 최소 \d+건/)).toBeVisible();
  const applications = await (await admin.request.get(`/api/learning/rules/${ruleId}`)).json() as { versions: Array<{ application_count: number }> };
  expect(applications.versions[0].application_count).toBeGreaterThanOrEqual(1);

  // 6. Stop: new Config version without the rule; history is kept.
  await page.getByLabel('결정 사유').fill('E2E: 중단');
  await page.getByRole('button', { name: '중단', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('규칙을 중단했습니다');
  await expect(page.getByText(/상태 중단/)).toBeVisible();
  const after = await (await admin.request.get('/api/policy/active')).json() as { version: number; config: { rules: unknown[] } };
  expect(after.config.rules.length).toBe(0);
  expect(after.version).toBeGreaterThan(active.version);
  await expect(page.locator('.learning-timeline')).toContainText('중단');
  await expect(page.getByTestId('used-count')).toHaveText(String(apiUsed));
});
