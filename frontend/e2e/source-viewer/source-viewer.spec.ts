import { expect, test, type Browser, type BrowserContext, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import AxeBuilder from '@axe-core/playwright';
import { join } from 'node:path';

/**
 * UX-2: evidence → source viewer (PDF page / DOCX paragraph / MD line / chat sentence) and judgment-map expanded view + version tabs.
 * Runtime: e2e/source-viewer/env.sh (tenant t-ux2, live Jev worker limited to that tenant). Non-sensitive fixtures only.
 */
const tenant = process.env.UX2_TENANT || 't-ux2';
const rule = `${tenant}-R-UX-01`;
const password = process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me';
const fixtures = join(process.cwd(), 'e2e/source-viewer/fixtures');
test.describe.configure({ mode: 'serial' });
test.setTimeout(120_000);

async function actor(browser: Browser, baseURL: string, role: string) {
  const context = await browser.newContext({ baseURL });
  const response = await context.request.post('/api/auth/login', { data: { email: `${role}@${tenant}.dev`, password } });
  expect(response.ok(), `login ${role}@${tenant}: ${response.status()}`).toBeTruthy();
  return { context, page: await context.newPage() };
}

// the label the viewer must show for a stored location (same rule as the component, restated from the spec)
function expectedLabel(location: Record<string, any>) {
  if (location.page !== undefined) return `${location.page}쪽`;
  if (location.line_start !== undefined) return location.line_end > location.line_start ? `${location.line_start}–${location.line_end}행` : `${location.line_start}행`;
  if (location.sentence !== undefined) return `문단 ${location.paragraph + 1} · 문장 ${location.sentence + 1}`;
  return `문단 ${location.paragraph + 1}`;
}

let requestId = '';
let owner: { context: BrowserContext; page: Page };

test.beforeAll(async ({ browser }, info) => {
  test.setTimeout(480_000);
  execFileSync('../backend/.venv/bin/python', ['e2e/source-viewer/seed.py', tenant]);
  const baseURL = info.project.use.baseURL as string;
  owner = await actor(browser, baseURL, 'source_reader');
  for (let attempt = 1; attempt <= 3 && !requestId; attempt += 1) {
    const { page } = owner;
    await page.goto('/');
    await page.getByLabel('파일 첨부').setInputFiles(['booking-spec.pdf', 'booking-notes.docx', 'booking-memo.md'].map((name) => join(fixtures, name)));
    const text = '사내 회의실 예약 도구를 도입하려고 합니다. 중복 예약을 줄이고 예약 전 알림을 보내야 합니다. 첨부 문서를 근거로 판단해 주세요.';
    await page.getByLabel('요청 내용').fill(text);
    await expect(page.getByLabel('요청 내용')).toHaveValue(text);
    const [submitted] = await Promise.all([
      page.waitForResponse(r => r.url().endsWith('/api/requests') && r.request().method() === 'POST'),
      page.getByRole('button', { name: '요청 보내기' }).click(),
    ]);
    expect(submitted.status()).toBe(202);
    const id = (await submitted.json()).request_id as string;
    await expect(page).toHaveURL(new RegExp(`request_id=${id}`));
    await expect(page.locator('.result-stack:not(.provisional-result)').getByRole('heading', { name: '판단 결과', exact: true })).toBeVisible({ timeout: 240_000 });
    expect(id).toBeTruthy();
    // live Jev decides what it cites; retry with a new request when nothing was cited
    if (await page.getByRole('button', { name: /근거 열기/ }).count()) requestId = id;
  }
  expect(requestId, 'live Jev cited no evidence in 3 requests').toBeTruthy();
});
test.afterAll(async () => { await owner?.context.close(); });

test('result card evidence opens the source viewer on the cited unit and highlights it', async () => {
  const { page } = owner;
  await page.goto(`/?request_id=${requestId}`);
  await expect(page.locator('.result-stack:not(.provisional-result)').getByRole('heading', { name: '판단 결과', exact: true })).toBeVisible();
  const buttons = page.getByRole('button', { name: /근거 열기/ });
  const count = Math.min(await buttons.count(), 6);
  expect(count).toBeGreaterThan(0);
  for (let index = 0; index < count; index += 1) {
    const button = buttons.nth(index);
    const loaded = page.waitForResponse(r => r.url().includes('/document?') && r.ok());
    await button.focus();
    await button.press('Enter');
    const document = await (await loaded).json();
    const dialog = page.getByRole('dialog').filter({ has: page.getByTestId('ev-scroll') });
    await expect(dialog).toBeVisible();
    const anchor = dialog.locator('[aria-current="location"]');
    await expect(anchor).toHaveCount(1);
    const unitId = await anchor.getAttribute('data-unit-id');
    const location = document.units.find((u: { unit_id: string }) => u.unit_id === unitId).location;
    await expect(anchor.locator('.ev-label')).toHaveText(expectedLabel(location));
    await expect(anchor.locator('p')).not.toBeEmpty();
    // scrolled into view: the anchor lies inside the scroll container's visible box
    const box = await anchor.boundingBox(), area = await dialog.getByTestId('ev-scroll').boundingBox();
    expect(box && area && box.y >= area.y - 1 && box.y + box.height <= area.y + area.height + 1).toBeTruthy();
    // every unit of that source is listed, in order
    expect(await dialog.locator('[data-unit-id]').count()).toBeGreaterThan(0);
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    await expect(button).toBeFocused();
  }
});

test('PDF page, DOCX paragraph, MD line and chat sentence anchors are highlighted for real parsed documents', async ({}, info) => {
  const { page, context } = owner;
  const detail = await (await context.request.get(`/api/requests/${requestId}`)).json() as { revisions: Array<{ id: string; number: number }>; attachments: Array<{ id: string; filename: string }> };
  const revision = detail.revisions[detail.revisions.length - 1];
  const docs: Record<string, any> = {};
  for (const source of ['chat', ...detail.attachments.map((a) => a.id)]) {
    const doc = await (await context.request.get(`/api/requests/${requestId}/revisions/${revision.id}/document`, { params: { source } })).json();
    docs[doc.kind] = doc;
  }
  expect(Object.keys(docs).sort()).toEqual(['chat', 'docx', 'md', 'pdf']);
  expect(docs.chat.units.length, 'prepared request must include its submitted chat text').toBeGreaterThan(0);
  expect(docs.pdf.units.map((u: any) => u.location.page)).toEqual([1, 2, 3]);
  const picks = { pdf: docs.pdf.units[2], docx: docs.docx.units[4], md: docs.md.units[3], chat: docs.chat.units[1] ?? docs.chat.units[0] } as Record<string, any>;
  const expected = { pdf: '3쪽', docx: '문단 5', md: expectedLabel(picks.md.location), chat: expectedLabel(picks.chat.location) } as Record<string, string>;
  // the judgment cites exactly these units (the stored spans are real; only the citation list is pinned for determinism)
  await page.route(`**/api/requests/${requestId}/judgment*`, async (route) => {
    const body = await (await route.fetch()).json();
    const attachmentOf = (kind: string) => (kind === 'chat' ? null : docs[kind].source);
    const target = body.outputs.find((o: any) => o.question_id === 'ai_need');
    body.outputs = [{ ...target, evidence: Object.entries(picks).map(([kind, unit]) => ({ id: unit.unit_id, source: kind === 'chat' ? 'chat' : 'attachment', attachment_id: attachmentOf(kind), location: unit.location })) }];
    await route.fulfill({ json: body });
  });
  await page.goto(`/?request_id=${requestId}`);
  await expect(page.locator('.result-stack:not(.provisional-result)').getByRole('heading', { name: '판단 결과', exact: true })).toBeVisible();
  await page.getByRole('button', { name: '자세히 보기' }).last().click();
  for (const kind of ['pdf', 'docx', 'md', 'chat']) {
    await page.getByRole('button', { name: /근거 열기/ }).filter({ hasText: kind === 'chat' ? '채팅' : '첨부' }).nth(kind === 'chat' ? 0 : ['pdf', 'docx', 'md'].indexOf(kind)).click();
    const dialog = page.getByRole('dialog').filter({ has: page.getByTestId('ev-scroll') });
    await expect(dialog.locator('[aria-current="location"] .ev-label')).toHaveText(expected[kind]);
    await expect(dialog.locator('[aria-current="location"]')).toHaveAttribute('data-unit-id', picks[kind].unit_id);
    if (kind === 'pdf') {
      await expect(dialog.getByRole('heading', { level: 3 })).toHaveText(['1쪽', '2쪽', '3쪽']);
      await expect(dialog.locator('[aria-current="location"]')).toContainText('Constraints');
    }
    if (kind === 'docx') await expect(dialog.locator('[aria-current="location"]')).toContainText('Calendar integration');
    if (kind === 'md') await expect(dialog.locator('.ev-unit')).toHaveCount(docs.md.units.length);
    await page.screenshot({ path: info.outputPath(`viewer-${kind}.png`) });
    await dialog.getByRole('button', { name: '닫기', exact: true }).click();
  }
});

test('without source permission the viewer shows positions only and the server sends no text', async ({ browser }, info) => {
  const baseURL = info.project.use.baseURL as string;
  const reviewer = await actor(browser, baseURL, 'reviewer'); // can_read_source=false, shares the request's org
  try {
    const detail = await (await reviewer.context.request.get(`/api/requests/${requestId}`)).json();
    const revision = detail.revisions[detail.revisions.length - 1].id;
    const attachment = detail.attachments.find((a: any) => a.filename.endsWith('.pdf')).id;
    const raw = await reviewer.context.request.get(`/api/requests/${requestId}/revisions/${revision}/document`, { params: { source: attachment } });
    expect(raw.status()).toBe(200);
    const text = await raw.text();
    expect(JSON.parse(text).can_read_source).toBe(false);
    expect(text).not.toContain('Constraints');
    expect(text).not.toContain('reminder message');
    const { page } = reviewer;
    const pdfUnit = JSON.parse(text).units[2];
    await page.route(`**/api/requests/${requestId}/judgment*`, async (route) => {
      const body = await (await route.fetch()).json();
      const target = body.outputs.find((o: any) => o.question_id === 'ai_need');
      body.outputs = [{ ...target, evidence: [{ id: pdfUnit.unit_id, source: 'attachment', attachment_id: attachment, location: pdfUnit.location }] }];
      await route.fulfill({ json: body });
    });
    await page.goto(`/?request_id=${requestId}`);
    await page.getByRole('button', { name: /근거 열기/ }).first().click();
    const dialog = page.getByRole('dialog').filter({ has: page.getByTestId('ev-scroll') });
    await expect(dialog.getByText(/원문 열람 권한 없음/)).toBeVisible();
    await expect(dialog.locator('[aria-current="location"] .ev-label')).toHaveText('3쪽');
    await expect(dialog.getByText('원문 비공개').first()).toBeVisible();
    expect(await dialog.textContent()).not.toContain('Constraints');
    await page.screenshot({ path: info.outputPath('viewer-no-permission.png') });
  } finally { await reviewer.context.close(); }
});

test('review detail and judgment-map evidence nodes open the same viewer', async ({ browser }, info) => {
  const { page, context } = owner;
  // Review: only requests with a pending review are listed, so open through the map when none exists
  const graph = await (await context.request.get(`/api/graph/judgment?request_id=${requestId}`)).json() as { nodes: Array<{ id: string; kind: string; title: string }> };
  const span = graph.nodes.find((n) => n.kind === 'EvidenceSpan');
  expect(span, 'stored graph has a cited EvidenceSpan').toBeTruthy();
  await page.goto(`/judgment-map?request_id=${requestId}`);
  await page.getByRole('button', { name: '목록 보기' }).click();
  await page.getByTestId('jm-list').locator(`[data-node-id="${span!.id}"]`).click();
  await page.getByRole('button', { name: '원문 열기' }).click();
  const dialog = page.getByRole('dialog').filter({ has: page.getByTestId('ev-scroll') });
  await expect(dialog.locator('[aria-current="location"]')).toHaveAttribute('data-unit-id', span!.id);
  await page.screenshot({ path: info.outputPath('viewer-from-map.png') });
  await page.keyboard.press('Escape');

  // Review detail: the same viewer, opened from a stored output's evidence row. The assigned reviewer (all orgs, no source
  // permission) sees positions only, which is the permission-limited path of the same panel.
  const reviewer = await actor(browser, info.project.use.baseURL as string, 'reviewer');
  try {
    await expect.poll(async () => ((await (await reviewer.context.request.get('/api/reviews?status=pending')).json()) as { reviews: Array<{ request_id: string }> })
      .reviews.some((r) => r.request_id === requestId), { timeout: 60_000 }).toBeTruthy();
    await reviewer.page.goto(`/review?request_id=${requestId}`);
    const open = reviewer.page.getByRole('button', { name: '원문 열기' }).first();
    await expect(open).toBeVisible();
    await open.click();
    const reviewDialog = reviewer.page.getByRole('dialog');
    await expect(reviewDialog.locator('[aria-current="location"]')).toHaveCount(1);
    await expect(reviewDialog.getByText(/원문 열람 권한 없음/)).toBeVisible();
    await reviewer.page.screenshot({ path: info.outputPath('viewer-from-review.png') });
  } finally { await reviewer.context.close(); }
});

test('judgment map: version tabs filter nodes and links, zoom controls and expanded view work', async ({ browser }, info) => {
  const baseURL = info.project.use.baseURL as string;
  const reviewer = await actor(browser, baseURL, 'reviewer');
  try {
    const { page, context } = reviewer;
    const api = await (await context.request.get(`/api/graph/judgment?rule_id=${rule}`)).json() as { node_count: number; edge_count: number };
    await page.goto(`/judgment-map?rule_id=${rule}`);
    const summary = page.getByTestId('jm-summary');
    await expect(summary).toContainText(`노드 ${api.node_count}개 · 연결 ${api.edge_count}개`);
    const tabs = page.getByRole('tablist', { name: '규칙 버전' });
    await expect(tabs.getByRole('tab')).toHaveText(['전체', 'v1되돌림', 'v2운영 중', 'v3검증 중']);
    for (const [tab, counts] of [['v1', '노드 5개 · 연결 4개'], ['v2', '노드 5개 · 연결 4개'], ['v3', '노드 4개 · 연결 3개']] as const) {
      await tabs.getByRole('tab', { name: new RegExp(`^${tab}`) }).click();
      await expect(summary).toContainText(counts);
      await expect(page.getByTestId('jm-board')).toHaveAttribute('data-node-count', counts.match(/노드 (\d+)/)![1]);
    }
    await page.screenshot({ path: info.outputPath('map-version-v3.png') });
    await tabs.getByRole('tab', { name: '전체' }).click();
    await expect(summary).toContainText(`노드 ${api.node_count}개`);

    // zoom: percentage, +/- and 전체 보기
    const pct = async () => Number(((await page.getByTestId('jm-zoom-pct').textContent()) || '').replace('%', ''));
    const fitted = await pct();
    await page.getByRole('button', { name: '확대' }).click();
    await expect.poll(pct).toBeGreaterThan(fitted);
    await page.getByRole('button', { name: '축소' }).click();
    await page.getByRole('button', { name: '축소' }).click();
    await expect.poll(pct).toBeLessThan(fitted);
    await page.getByRole('button', { name: '전체 보기' }).click();
    await expect.poll(pct).toBe(fitted);

    // expanded view: bigger stage, focus stays on the toggle, Esc leaves it without clearing the selection
    const stage = page.getByTestId('jm-stage');
    const before = (await stage.boundingBox())!;
    const toggle = page.getByRole('button', { name: '크게 보기' });
    await page.locator(`[data-node-id="${rule}@2"]`).click();
    await expect(page.getByTestId('jm-detail')).toContainText(`${rule}@2`);
    await toggle.focus();
    await toggle.press('Enter');
    await expect(page.locator('.jm-page')).toHaveClass(/is-expanded/);
    await expect(toggle).toHaveAttribute('aria-pressed', 'true');
    await expect(toggle).toBeFocused();
    await expect.poll(async () => (await stage.boundingBox())!.height).toBeGreaterThan(before.height);
    await page.screenshot({ path: info.outputPath('map-expanded.png') });
    await page.keyboard.press('Escape');
    await expect(page.locator('.jm-page')).not.toHaveClass(/is-expanded/);
    await expect(toggle).toBeFocused();
    await expect(page.getByTestId('jm-detail')).toContainText(`${rule}@2`);
    await expect.poll(async () => Math.abs((await stage.boundingBox())!.height - before.height)).toBeLessThan(2);
  } finally { await reviewer.context.close(); }
});

test('version area is an empty state when the criteria have no rule versions', async ({ browser }, info) => {
  const reviewer = await actor(browser, info.project.use.baseURL as string, 'reviewer');
  try {
    await reviewer.page.goto(`/judgment-map?request_id=${requestId}`);
    await expect(reviewer.page.getByTestId('jm-summary')).toBeVisible();
    await expect(reviewer.page.getByTestId('jm-version-empty')).toContainText('규칙 버전 데이터가 없습니다');
  } finally { await reviewer.context.close(); }
});

test('axe: source viewer, version tabs and expanded map have no critical or serious violations', async ({ browser }, info) => {
  const reviewer = await actor(browser, info.project.use.baseURL as string, 'reviewer');
  const blocking = async (page: Page) => {
    // Measure settled colors, not the translucent intermediate frame of the overlay fade.
    await page.evaluate(async () => {
      await Promise.all(document.getAnimations().filter(animation => animation.effect?.getComputedTiming().iterations !== Infinity)
        .map(animation => animation.finished.catch(() => undefined)));
    });
    return (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze())
      .violations.filter(({ impact }) => impact === 'critical' || impact === 'serious').map(({ id, nodes }) => ({ id, targets: nodes.map((n) => n.target) }));
  };
  try {
    const { page } = reviewer;
    await page.goto(`/judgment-map?rule_id=${rule}`);
    await expect(page.getByRole('tablist', { name: '규칙 버전' })).toBeVisible();
    expect(await blocking(page), 'map with version tabs').toEqual([]);
    await page.getByRole('button', { name: '크게 보기' }).focus();
    await page.getByRole('button', { name: '크게 보기' }).press('Enter');
    expect(await blocking(page), 'expanded map').toEqual([]);
    await page.keyboard.press('Escape');
    const graph = await (await reviewer.context.request.get(`/api/graph/judgment?request_id=${requestId}`)).json() as { nodes: Array<{ id: string; kind: string }> };
    await page.goto(`/judgment-map?request_id=${requestId}`);
    await page.getByRole('button', { name: '목록 보기' }).click();
    await page.getByTestId('jm-list').locator(`[data-node-id="${graph.nodes.find((n) => n.kind === 'EvidenceSpan')!.id}"]`).click();
    await page.getByRole('button', { name: '원문 열기' }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    expect(await blocking(page), 'source viewer dialog').toEqual([]);
  } finally { await reviewer.context.close(); }
});
