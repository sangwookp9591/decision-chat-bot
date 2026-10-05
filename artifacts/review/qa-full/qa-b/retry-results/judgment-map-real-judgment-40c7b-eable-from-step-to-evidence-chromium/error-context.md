# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: judgment-map.spec.ts >> real judgment and correction render as the stored graph, traceable from step to evidence
- Location: e2e/judgment-map.spec.ts:54:1

# Error details

```
Error: submit failed: 503

expect(received).toBeTruthy()

Received: false
```

# Test source

```ts
  1   | import { expect, test, type APIRequestContext, type Page } from '@playwright/test';
  2   | 
  3   | const password = process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me';
  4   | type Graph = { nodes: Array<{ id: string; kind: string; layer: number }>; edges: unknown[]; node_count: number; edge_count: number; layers: Array<{ layer: number; count: number }> };
  5   | 
  6   | async function login(api: APIRequestContext, role: string) {
  7   |   const response = await api.post('/api/auth/login', { data: { email: `${role}@${process.env.E2E_TENANT || 't-alpha'}.dev`, password } });
  8   |   expect(response.ok(), `login ${role} failed: ${response.status()}`).toBeTruthy();
  9   |   const state = await api.storageState();
  10  |   return state.cookies.find((cookie) => cookie.name === 'jev_csrf')?.value || '';
  11  | }
  12  | 
  13  | // One real judgment (live Jev) and one reviewer correction are created through the public API.
  14  | // Live Jev decides whether a span is cited, so up to three requests are tried until one cites evidence.
  15  | async function seedJudgmentWithCorrection(page: Page) {
  16  |   const api = page.request;
  17  |   for (let attempt = 1; attempt <= 3; attempt += 1) {
  18  |     let csrf = await login(api, 'requester');
  19  |     const submitted = await api.post('/api/requests', {
  20  |       headers: { 'Idempotency-Key': crypto.randomUUID(), 'X-CSRF-Token': csrf },
  21  |       multipart: {
  22  |         text: `임상시험 이상반응 보고서를 자동으로 분류하고 안전성 담당자에게 전달하는 기능이 필요합니다. 규제 보고 기한 확인이 필요합니다. (시도 ${attempt})`,
  23  |         files: { name: 'safety-notes.md', mimeType: 'text/markdown', buffer: Buffer.from('이상반응 보고서는 접수 후 24시간 이내 안전성 담당자가 확인합니다. 규제 보고 기한과 담당 부서를 함께 표시해야 합니다.') },
  24  |       },
  25  |     });
> 26  |     expect(submitted.ok(), `submit failed: ${submitted.status()}`).toBeTruthy();
      |                                                                    ^ Error: submit failed: 503
  27  |     const created = await submitted.json() as { request_id?: string; id?: string };
  28  |     const requestId = (created.request_id || created.id) as string;
  29  |     expect(requestId).toBeTruthy();
  30  |     csrf = await login(api, 'reviewer');
  31  |     let review: { id: string; request_id: string } | undefined;
  32  |     await expect.poll(async () => {
  33  |       const list = await (await api.get('/api/reviews?status=pending')).json() as { reviews: Array<{ id: string; request_id: string }> };
  34  |       review = list.reviews.find((row) => row.request_id === requestId);
  35  |       return Boolean(review);
  36  |     }, { timeout: 150_000, intervals: [3000], message: 'review for the judged request never appeared' }).toBeTruthy();
  37  |     const stored = await (await api.get(`/api/graph/judgment?request_id=${requestId}`)).json() as Graph;
  38  |     if (!(stored.edges as Array<{ type: string }>).some((edge) => edge.type === 'CITES') && attempt < 3) continue;
  39  |     const detail = await (await api.get(`/api/reviews/${review!.id}`)).json() as { review: Record<string, any>; final_classifications: Record<string, string> };
  40  |     const current = detail.final_classifications.ai_need;
  41  |     const corrected = ['필요', '불필요', '혼합'].find((value) => value !== current) as string;
  42  |     const decided = await api.post(`/api/reviews/${review!.id}/decision`, {
  43  |       headers: { 'Idempotency-Key': crypto.randomUUID(), 'X-CSRF-Token': csrf },
  44  |       data: { action: 'approve_with_changes', request_id: requestId, input_revision: detail.review.revision_id, run_id: detail.review.run_id,
  45  |         draft_version: detail.review.draft_version, review_version: detail.review.review_version,
  46  |         changes: { classifications: { ai_need: corrected } }, reason: '판단 맵 E2E: 분류 수정 승인' },
  47  |     });
  48  |     expect(decided.ok(), `decision failed: ${decided.status()} ${await decided.text()}`).toBeTruthy();
  49  |     return requestId;
  50  |   }
  51  |   throw new Error('unreachable');
  52  | }
  53  | 
  54  | test('real judgment and correction render as the stored graph, traceable from step to evidence', async ({ page }) => {
  55  |   test.setTimeout(720_000);
  56  |   // E2E_REQUEST_ID reuses a request created by an earlier run (skips the live Jev call).
  57  |   const requestId = process.env.E2E_REQUEST_ID || await seedJudgmentWithCorrection(page);
  58  |   if (process.env.E2E_REQUEST_ID) await login(page.request, 'reviewer');
  59  |   const graph = await (await page.request.get(`/api/graph/judgment?request_id=${requestId}`)).json() as Graph;
  60  |   expect(graph.nodes.some((n) => n.kind === 'Correction')).toBeTruthy();
  61  |   expect(graph.nodes.some((n) => n.kind === 'ReviewDecision')).toBeTruthy();
  62  |   expect(graph.nodes.some((n) => n.kind === 'ModelOutput')).toBeTruthy();
  63  | 
  64  |   await page.goto(`/judgment-map?request_id=${requestId}`);
  65  |   await expect(page.getByRole('heading', { name: '입체 판단 맵' })).toBeVisible();
  66  |   const board = page.getByTestId('jm-board');
  67  |   await expect(board).toHaveAttribute('data-node-count', String(graph.node_count));
  68  |   await expect(board).toHaveAttribute('data-edge-count', String(graph.edge_count));
  69  |   await expect(page.getByTestId('jm-summary')).toContainText(`노드 ${graph.node_count}개 · 연결 ${graph.edge_count}개`);
  70  |   for (const layer of graph.layers) await expect(page.getByTestId(`jm-layer-count-${layer.layer}`)).toContainText(String(layer.count));
  71  | 
  72  |   // 3D map: node ids on screen equal the API node ids (bundled groups expand in list view below).
  73  |   const mapIds = await page.locator('.jm-node:not(.is-group)').evaluateAll((els) => els.map((el) => (el as HTMLElement).dataset.nodeId));
  74  |   for (const id of mapIds) expect(graph.nodes.map((n) => n.id)).toContain(id);
  75  |   await expect(page.locator('.jm-line').first()).toBeAttached();
  76  |   await expect(page.getByTestId('jm-zoom-pct')).toContainText('%');
  77  |   const before = await page.getByTestId('jm-zoom-pct').innerText();
  78  |   await page.getByRole('button', { name: '확대' }).click();
  79  |   await expect(page.getByTestId('jm-zoom-pct')).not.toHaveText(before);
  80  |   await page.getByRole('button', { name: '전체 보기' }).click();
  81  | 
  82  |   // Trace: execution step -> model output -> evidence span, through stored relationships only.
  83  |   const step = page.locator('.jm-node[data-kind="RunStep"]').first();
  84  |   await expect(step).toBeVisible();
  85  |   await step.click();
  86  |   await expect(page.getByTestId('jm-detail')).toContainText('5계층');
  87  |   await expect(page.getByTestId('jm-up-count')).toContainText(/근거 쪽으로 [1-9]\d*개/);
  88  |   await expect(page.locator('.jm-node[data-kind="EvidenceSpan"].is-path').first()).toBeVisible();
  89  |   const traced = await page.request.get(`/api/graph/judgment/path?node_id=${await step.getAttribute('data-node-id')}&direction=up`);
  90  |   const pathBody = await traced.json() as { nodes: Array<{ kind: string }> };
  91  |   expect(pathBody.nodes.map((n) => n.kind)).toContain('EvidenceSpan');
  92  |   await expect(page.getByRole('link', { name: 'Flow에서 보기' })).toHaveAttribute('href', /\/observatory\?run_id=run_/);
  93  |   await page.keyboard.press('Escape');
  94  |   await expect(page.getByTestId('jm-up-count')).toHaveCount(0);
  95  | 
  96  |   // List view: same ids as the API, keyboard moves between nodes and layers, Enter selects.
  97  |   await page.getByRole('button', { name: '목록 보기' }).click();
  98  |   const listIds = await page.locator('.jm-item').evaluateAll((els) => els.map((el) => (el as HTMLElement).dataset.nodeId).sort());
  99  |   expect(listIds).toEqual(graph.nodes.map((n) => n.id).sort());
  100 |   const first = page.locator('.jm-item[data-kind="ModelOutput"]').first();
  101 |   await first.focus();
  102 |   const startId = await first.getAttribute('data-node-id');
  103 |   await page.keyboard.press('ArrowRight');
  104 |   const focused = () => page.evaluate(() => (document.activeElement as HTMLElement).dataset.nodeId);
  105 |   await expect.poll(focused).not.toBe(startId);
  106 |   const afterRight = await focused();
  107 |   const layerOf = (id: string | null | undefined) => graph.nodes.find((n) => n.id === id)?.layer;
  108 |   await page.keyboard.press('ArrowDown');
  109 |   await expect.poll(async () => layerOf(await focused()) ?? 0).toBeGreaterThan(layerOf(afterRight) as number);
  110 |   await page.keyboard.press('Enter');
  111 |   await expect(page.getByTestId('jm-detail').getByRole('heading', { level: 2 })).toBeVisible();
  112 |   await expect(page.getByRole('table')).toContainText('관계');
  113 |   await page.keyboard.press('Escape');
  114 |   await expect(page.getByTestId('jm-up-count')).toHaveCount(0);
  115 | });
  116 | 
  117 | test('a role without graph access is refused', async ({ page }) => {
  118 |   await login(page.request, 'requester');
  119 |   const response = await page.request.get('/api/graph/judgment');
  120 |   expect(response.status()).toBe(403);
  121 | });
  122 | 
```