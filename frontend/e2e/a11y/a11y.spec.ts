import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { resolve } from 'node:path';

const tenant = process.env.E2E_TENANT || 't-t23';
const password = process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me';
const screens = [
  ['요청 접수', '/'], ['검토', '/review'], ['업무', '/tasks'],
  ['실행 관찰', '/observatory'], ['판단 맵 입체 보기', '/judgment-map'],
  ['판단 맵 목록 보기', '/judgment-map?view=list'], ['규칙 학습', '/learning'],
  ['모니터링', '/monitoring'], ['정책', '/policy'],
] as const;

async function login(page: Page, role = 'reviewer') {
  const response = await page.request.post('/api/auth/login', { data: { email: `${role}@${tenant}.dev`, password } });
  expect(response.ok(), `login failed: ${response.status()}`).toBeTruthy();
}

test('login screen has no critical or serious axe violations', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: '로그인이 필요합니다' })).toBeVisible();
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
  const blocking = results.violations.filter(({ impact }) => impact === 'critical' || impact === 'serious');
  expect(blocking, JSON.stringify(blocking.map(({ id, nodes }) => ({ id, targets: nodes.map((node) => node.target) })), null, 2)).toEqual([]);
});

test('all primary application screens have no critical or serious axe violations', async ({ page }) => {
  await login(page);
  for (const [name, path] of screens) {
    await page.goto(path);
    if (name === '판단 맵 목록 보기') await page.getByRole('button', { name: '목록 보기' }).click();
    await expect(page.locator('main')).toBeVisible();
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
    const blocking = results.violations.filter(({ impact }) => impact === 'critical' || impact === 'serious');
    expect(blocking, `${name}: ${JSON.stringify(blocking.map(({ id, nodes }) => ({ id, targets: nodes.map((node) => node.target) })), null, 2)}`).toEqual([]);
    const bodyText = await page.locator('body').innerText();
    expect(bodyText).not.toMatch(/\bDEMO\b|sample[_ -]?id/i);
    const mockBadges = page.locator('.environment-badge.mode-mock');
    if (await mockBadges.count()) await expect(mockBadges).toContainText(/mock/i);
    for (const status of await page.locator('.status-badge').all()) {
      await expect(status.locator('[aria-hidden="true"]')).toHaveCount(1);
      expect((await status.innerText()).trim().length).toBeGreaterThan(1);
    }
  }
});

test('shell, status, primary color and touch target contracts are visible', async ({ page }) => {
  await login(page);
  await page.goto('/');
  const primary = page.locator('button.primary').first();
  await expect(primary).toBeVisible();
  expect(await primary.evaluate((el) => getComputedStyle(el).color)).toBe('rgb(27, 23, 18)');
  const targets = await page.locator('.app-sidebar nav a, button.primary').evaluateAll((els) => els.map((el) => {
    const rect = el.getBoundingClientRect();
    return { name: (el.textContent || el.getAttribute('aria-label') || '').trim(), width: rect.width, height: rect.height };
  }).filter(({ width, height }) => width > 0 && height > 0));
  expect(targets.filter(({ width, height }) => width < 44 || height < 44), JSON.stringify(targets.filter(({ width, height }) => width < 44 || height < 44))).toEqual([]);
  for (const width of [1280, 960, 520, 375]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(page.locator('.app-sidebar nav')).toBeVisible();
    const sidebarPosition = await page.locator('.app-sidebar').evaluate((el) => getComputedStyle(el).position);
    expect(sidebarPosition).toBe(width > 960 ? 'fixed' : 'static');
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  }
  await page.setViewportSize({ width: 520, height: 900 });
  // The conversation is the intake page itself: no floating launcher or dialog anywhere in the app.
  await expect(page.getByRole('button', { name: /일동이와 채팅 열기/ })).toHaveCount(0);
  await expect(page.locator('.chat-launcher, .chat-panel')).toHaveCount(0);
  await expect(page.getByRole('log', { name: '일동이와의 대화' })).toHaveAttribute('aria-live', 'polite');
  // A11Y_SHOT_DIR keeps regression reruns from overwriting the archived t23 evidence PNGs.
  const shotDir = resolve(process.cwd(), process.env.A11Y_SHOT_DIR || '../artifacts/validation/t23');
  mkdirSync(shotDir, { recursive: true });
  await page.screenshot({ path: resolve(shotDir, `${test.info().project.name}-responsive-520.png`), fullPage: true });
});

test('reduced motion and Safari mascot media preference are respected', async ({ page, browserName }) => {
  await login(page);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await expect(page.locator('.chat-greeting [data-mascot="wave"]')).toHaveAttribute('src', /mascot\.png$/);
  await expect(page.locator('.chat-greeting video')).toHaveCount(0);
  if (browserName === 'webkit') {
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.reload();
    await expect(page.locator('.chat-greeting [data-mascot="wave"]')).toHaveAttribute('src', /wave\.webp$/);
  } else {
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.reload();
    await expect(page.locator('.chat-greeting video[data-mascot="wave"]')).toHaveAttribute('src', /wave\.webm$/);
  }
});

test('conversation is keyboard operable: examples, composer, attach and send need no pointer', async ({ page, browserName }) => {
  test.setTimeout(60_000);
  await login(page, 'requester');
  await page.goto('/');
  const first = page.getByRole('group', { name: '예시 요청' }).getByRole('button').first();
  await first.focus();
  await page.keyboard.press('Enter');
  const input = page.getByLabel('요청 내용');
  await expect(input).toBeFocused();
  await expect(input).toHaveValue(/\S/);
  const attach = page.getByLabel('파일 첨부');
  expect(await attach.evaluate((el) => (el as HTMLInputElement).tabIndex)).toBeGreaterThanOrEqual(0); // never removed from the tab order
  if (browserName === 'chromium') { // Safari's default Tab traversal skips some controls, so the order is asserted where it is defined
    await page.keyboard.press('Shift+Tab');
    await expect(attach).toBeFocused(); // attach sits right before the text field
    await page.keyboard.press('Tab'); await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: '요청 보내기' })).toBeFocused();
  } else { await attach.focus(); await expect(attach).toBeFocused(); }
  await input.focus();
  await page.keyboard.press('Control+Enter');
  await expect(page.getByRole('group', { name: '내가 보낸 요청' })).toBeVisible();
  await expect(page.getByRole('heading', { name: '분석 진행' })).toBeVisible();
});

test('keyboard submits a real request and opens its saved evidence', async ({ page }) => {
  test.setTimeout(240_000);
  await login(page, 'requester');
  await page.goto('/');
  const input = page.getByLabel('요청 내용');
  await input.fill(`키보드 접근성 검증 ${Date.now()}: 임상시험 이상반응 보고를 안전성 담당자가 확인하고 규제 기한 안에 처리해야 합니다.`);
  await page.getByLabel('파일 첨부').setInputFiles({ name: 'a11y-validation.md', mimeType: 'text/markdown', buffer: Buffer.from('이상반응 보고서는 24시간 이내 안전성 담당자가 확인하고 규제 보고 기한을 검토합니다.') });
  const submit = page.getByRole('button', { name: '요청 보내기' });
  await submit.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('.result-stack:not(.provisional-result)').getByRole('heading', { name: '판단 결과', exact: true })).toBeVisible({ timeout: 180_000 });
  const evidence = page.getByRole('button', { name: /근거 열기|근거 패널 열기/ }).first();
  await evidence.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('heading', { name: '근거 원문' })).toBeVisible();
  const requestId = await page.locator('.request-list button code').first().innerText();
  await page.request.post('/api/auth/login', { data: { email: `reviewer@${tenant}.dev`, password } });
  await page.goto('/review');
  const reviewRow = page.getByRole('button', { name: new RegExp(requestId) });
  await expect(reviewRow).toBeVisible({ timeout: 30_000 });
  await reviewRow.focus();
  await page.keyboard.press('Enter');
  const approve = page.getByRole('button', { name: '승인', exact: true });
  await expect(approve).toBeVisible();
  await approve.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('status')).toContainText(/결정|승인|저장/, { timeout: 30_000 });
  await page.request.post('/api/auth/login', { data: { email: `reviewer@${tenant}.dev`, password } });
  await page.goto(`/judgment-map?request_id=${encodeURIComponent(requestId)}`);
  await expect(page.getByRole('heading', { name: '입체 판단 맵' })).toBeVisible();
  await page.getByRole('button', { name: '목록 보기' }).click();
  const firstNode = page.locator('.jm-item').first();
  await expect(firstNode).toBeVisible();
  await firstNode.focus();
  const initialNode = await firstNode.getAttribute('data-node-id');
  await page.keyboard.press('ArrowRight');
  await expect.poll(() => page.evaluate(() => (document.activeElement as HTMLElement).dataset.nodeId)).not.toBe(initialNode);
  await page.keyboard.press('Enter');
  await expect(page.getByTestId('jm-detail').getByRole('heading', { level: 2 })).toBeVisible();
});
