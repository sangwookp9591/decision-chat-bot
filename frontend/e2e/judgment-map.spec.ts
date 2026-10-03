import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const password = process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me';
type Graph = { nodes: Array<{ id: string; kind: string; layer: number }>; edges: unknown[]; node_count: number; edge_count: number; layers: Array<{ layer: number; count: number }> };

async function login(api: APIRequestContext, role: string) {
  const response = await api.post('/api/auth/login', { data: { email: `${role}@t-alpha.dev`, password } });
  expect(response.ok(), `login ${role} failed: ${response.status()}`).toBeTruthy();
  const state = await api.storageState();
  return state.cookies.find((cookie) => cookie.name === 'jev_csrf')?.value || '';
}

// One real judgment (live Jev) and one reviewer correction are created through the public API.
// Live Jev decides whether a span is cited, so up to three requests are tried until one cites evidence.
async function seedJudgmentWithCorrection(page: Page) {
  const api = page.request;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    let csrf = await login(api, 'requester');
    const submitted = await api.post('/api/requests', {
      headers: { 'Idempotency-Key': crypto.randomUUID(), 'X-CSRF-Token': csrf },
      multipart: {
        text: `임상시험 이상반응 보고서를 자동으로 분류하고 안전성 담당자에게 전달하는 기능이 필요합니다. 규제 보고 기한 확인이 필요합니다. (시도 ${attempt})`,
        files: { name: 'safety-notes.md', mimeType: 'text/markdown', buffer: Buffer.from('이상반응 보고서는 접수 후 24시간 이내 안전성 담당자가 확인합니다. 규제 보고 기한과 담당 부서를 함께 표시해야 합니다.') },
      },
    });
    expect(submitted.ok(), `submit failed: ${submitted.status()}`).toBeTruthy();
    const created = await submitted.json() as { request_id?: string; id?: string };
    const requestId = (created.request_id || created.id) as string;
    expect(requestId).toBeTruthy();
    csrf = await login(api, 'reviewer');
    let review: { id: string; request_id: string } | undefined;
    await expect.poll(async () => {
      const list = await (await api.get('/api/reviews?status=pending')).json() as { reviews: Array<{ id: string; request_id: string }> };
      review = list.reviews.find((row) => row.request_id === requestId);
      return Boolean(review);
    }, { timeout: 150_000, intervals: [3000], message: 'review for the judged request never appeared' }).toBeTruthy();
    const stored = await (await api.get(`/api/graph/judgment?request_id=${requestId}`)).json() as Graph;
    if (!(stored.edges as Array<{ type: string }>).some((edge) => edge.type === 'CITES') && attempt < 3) continue;
    const detail = await (await api.get(`/api/reviews/${review!.id}`)).json() as { review: Record<string, any>; final_classifications: Record<string, string> };
    const current = detail.final_classifications.ai_need;
    const corrected = ['필요', '불필요', '혼합'].find((value) => value !== current) as string;
    const decided = await api.post(`/api/reviews/${review!.id}/decision`, {
      headers: { 'Idempotency-Key': crypto.randomUUID(), 'X-CSRF-Token': csrf },
      data: { action: 'approve_with_changes', request_id: requestId, input_revision: detail.review.revision_id, run_id: detail.review.run_id,
        draft_version: detail.review.draft_version, review_version: detail.review.review_version,
        changes: { classifications: { ai_need: corrected } }, reason: '판단 맵 E2E: 분류 수정 승인' },
    });
    expect(decided.ok(), `decision failed: ${decided.status()} ${await decided.text()}`).toBeTruthy();
    return requestId;
  }
  throw new Error('unreachable');
}

test('real judgment and correction render as the stored graph, traceable from step to evidence', async ({ page }) => {
  test.setTimeout(720_000);
  // E2E_REQUEST_ID reuses a request created by an earlier run (skips the live Jev call).
  const requestId = process.env.E2E_REQUEST_ID || await seedJudgmentWithCorrection(page);
  if (process.env.E2E_REQUEST_ID) await login(page.request, 'reviewer');
  const graph = await (await page.request.get(`/api/graph/judgment?request_id=${requestId}`)).json() as Graph;
  expect(graph.nodes.some((n) => n.kind === 'Correction')).toBeTruthy();
  expect(graph.nodes.some((n) => n.kind === 'ReviewDecision')).toBeTruthy();
  expect(graph.nodes.some((n) => n.kind === 'ModelOutput')).toBeTruthy();

  await page.goto(`/judgment-map?request_id=${requestId}`);
  await expect(page.getByRole('heading', { name: '입체 판단 맵' })).toBeVisible();
  const board = page.getByTestId('jm-board');
  await expect(board).toHaveAttribute('data-node-count', String(graph.node_count));
  await expect(board).toHaveAttribute('data-edge-count', String(graph.edge_count));
  await expect(page.getByTestId('jm-summary')).toContainText(`노드 ${graph.node_count}개 · 연결 ${graph.edge_count}개`);
  for (const layer of graph.layers) await expect(page.getByTestId(`jm-layer-count-${layer.layer}`)).toContainText(String(layer.count));

  // 3D map: node ids on screen equal the API node ids (bundled groups expand in list view below).
  const mapIds = await page.locator('.jm-node:not(.is-group)').evaluateAll((els) => els.map((el) => (el as HTMLElement).dataset.nodeId));
  for (const id of mapIds) expect(graph.nodes.map((n) => n.id)).toContain(id);
  await expect(page.locator('.jm-line').first()).toBeAttached();
  await expect(page.getByTestId('jm-zoom-pct')).toContainText('%');
  const before = await page.getByTestId('jm-zoom-pct').innerText();
  await page.getByRole('button', { name: '확대' }).click();
  await expect(page.getByTestId('jm-zoom-pct')).not.toHaveText(before);
  await page.getByRole('button', { name: '전체 보기' }).click();

  // Trace: execution step -> model output -> evidence span, through stored relationships only.
  const step = page.locator('.jm-node[data-kind="RunStep"]').first();
  await expect(step).toBeVisible();
  await step.click();
  await expect(page.getByTestId('jm-detail')).toContainText('5계층');
  await expect(page.getByTestId('jm-up-count')).toContainText(/근거 쪽으로 [1-9]\d*개/);
  await expect(page.locator('.jm-node[data-kind="EvidenceSpan"].is-path').first()).toBeVisible();
  const traced = await page.request.get(`/api/graph/judgment/path?node_id=${await step.getAttribute('data-node-id')}&direction=up`);
  const pathBody = await traced.json() as { nodes: Array<{ kind: string }> };
  expect(pathBody.nodes.map((n) => n.kind)).toContain('EvidenceSpan');
  await expect(page.getByRole('link', { name: 'Flow에서 보기' })).toHaveAttribute('href', /\/observatory\?run_id=run_/);
  await page.keyboard.press('Escape');
  await expect(page.getByTestId('jm-up-count')).toHaveCount(0);

  // List view: same ids as the API, keyboard moves between nodes and layers, Enter selects.
  await page.getByRole('button', { name: '목록 보기' }).click();
  const listIds = await page.locator('.jm-item').evaluateAll((els) => els.map((el) => (el as HTMLElement).dataset.nodeId).sort());
  expect(listIds).toEqual(graph.nodes.map((n) => n.id).sort());
  const first = page.locator('.jm-item[data-kind="ModelOutput"]').first();
  await first.focus();
  const startId = await first.getAttribute('data-node-id');
  await page.keyboard.press('ArrowRight');
  const focused = () => page.evaluate(() => (document.activeElement as HTMLElement).dataset.nodeId);
  await expect.poll(focused).not.toBe(startId);
  const afterRight = await focused();
  const layerOf = (id: string | null | undefined) => graph.nodes.find((n) => n.id === id)?.layer;
  await page.keyboard.press('ArrowDown');
  await expect.poll(async () => layerOf(await focused()) ?? 0).toBeGreaterThan(layerOf(afterRight) as number);
  await page.keyboard.press('Enter');
  await expect(page.getByTestId('jm-detail').getByRole('heading', { level: 2 })).toBeVisible();
  await expect(page.getByRole('table')).toContainText('관계');
  await page.keyboard.press('Escape');
  await expect(page.getByTestId('jm-up-count')).toHaveCount(0);
});

test('a role without graph access is refused', async ({ page }) => {
  await login(page.request, 'requester');
  const response = await page.request.get('/api/graph/judgment');
  expect(response.status()).toBe(403);
});
