import { expect, test, type Browser, type Page } from '@playwright/test';

/** P4-04: no page may scroll horizontally at 375 / 520 px, also with a selected result / review / task (long ids, tables, code). */
const tenant = process.env.E2E_TENANT || 't-alpha';
const password = process.env.ILDONGI_DEV_PASSWORD || 'dev-only-change-me';
const baseURL = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173';
const widths = [375, 520];

async function as(browser: Browser, role: string, width: number) {
  const context = await browser.newContext({ baseURL, viewport: { width, height: 900 } });
  const login = await context.request.post('/api/auth/login', { data: { email: `${role}@${tenant}.dev`, password } });
  expect(login.ok(), `login ${role}: ${login.status()}`).toBeTruthy();
  return { context, page: await context.newPage() };
}

async function expectNoOverflow(page: Page, label: string, width: number) {
  await page.waitForTimeout(300);
  const metrics = await page.evaluate(() => {
    const root = document.scrollingElement as HTMLElement;
    const wide = [...document.querySelectorAll<HTMLElement>('body *')].filter((el) => (el.getBoundingClientRect().right > window.innerWidth + 1 || el.scrollWidth > el.clientWidth + 1) && !el.closest('nav,.table-scroll,.monitor-table-scroll,pre,[data-scroll-container]') && !['auto', 'scroll'].includes(getComputedStyle(el).overflowX))
      .slice(0, 5).map((el) => `${el.tagName.toLowerCase()}.${String(el.className).slice(0, 40)}`);
    return { scrollWidth: root.scrollWidth, innerWidth: window.innerWidth, wide };
  });
  expect(metrics.scrollWidth, `${label} @${width}: scrollWidth ${metrics.scrollWidth} > ${metrics.innerWidth}; wide: ${metrics.wide.join(', ')}`).toBeLessThanOrEqual(width);
}

for (const width of widths) {
  test.describe(`viewport ${width}px`, () => {
    test('Main with a selected result', async ({ browser }) => {
      const { context, page } = await as(browser, 'requester', width);
      const list = await (await context.request.get('/api/requests')).json();
      const ids: string[] = (list.items || []).map((item: { id: string }) => item.id).slice(0, 8);
      test.skip(!ids.length, 'no requests in this tenant');
      await page.goto('/'); await expectNoOverflow(page, 'Main (empty)', width);
      for (const id of ids) {
        await page.goto(`/?request_id=${id}`);
        await page.waitForTimeout(1200);
        await expectNoOverflow(page, `Main ${id}`, width);
      }
      await context.close();
    });
    test('Review detail', async ({ browser }) => {
      const { context, page } = await as(browser, 'reviewer', width);
      const reviews: Array<{ id: string }> = [];
      for (const status of ['pending', 'approved', 'rejected', 'info_requested']) reviews.push(...((await (await context.request.get(`/api/reviews?status=${status}`)).json()).reviews || []).slice(0, 3));
      test.skip(!reviews.length, 'no reviews in this tenant');
      await page.goto('/review'); await expectNoOverflow(page, 'Review (list)', width);
      for (const review of reviews) {
        await page.goto(`/review?review_id=${review.id}`);
        await expect(page.getByRole('heading', { name: '결정 이력' })).toBeVisible();
        await expectNoOverflow(page, `Review ${review.id}`, width);
      }
      await context.close();
    });
    test('Monitoring', async ({ browser }) => {
      const { context, page } = await as(browser, 'operator', width);
      await page.goto('/monitoring'); await expect(page.getByRole('heading', { name: '핵심 지표' })).toBeVisible();
      await expectNoOverflow(page, 'Monitoring', width); await context.close();
    });
    test('Learning with a selected candidate', async ({ browser }) => {
      const { context, page } = await as(browser, 'rule_admin', width);
      await page.goto('/learning'); await expect(page.locator('main')).toBeVisible();
      await expectNoOverflow(page, 'Learning (list)', width);
      const candidates = page.getByRole('button', { name: /cand_/ });
      const count = Math.min(await candidates.count(), 4);
      for (let i = 0; i < count; i++) { await candidates.nth(i).click(); await page.waitForTimeout(800); await expectNoOverflow(page, `Learning candidate ${i}`, width); }
      await context.close();
    });
    test('Tasks with a selected task', async ({ browser }) => {
      const { context, page } = await as(browser, 'team_member', width);
      await page.goto('/tasks'); await expect(page.getByRole('heading', { name: '업무', exact: true })).toBeVisible();
      await expectNoOverflow(page, 'Tasks (list)', width);
      const rows = page.locator('.task-list > button');
      const count = Math.min(await rows.count(), 4);
      for (let i = 0; i < count; i++) { await rows.nth(i).click(); await expect(page.getByRole('dialog', { name: '업무 상세' })).toBeVisible(); await expectNoOverflow(page, `Tasks detail ${i}`, width); await page.getByRole('dialog', { name: '업무 상세' }).getByRole('button', { name: '닫기' }).click(); }
      await context.close();
    });
    test('Observatory with a selected request', async ({ browser }) => {
      const { context, page } = await as(browser, 'operator', width);
      await page.goto('/observatory'); await expect(page.locator('main')).toBeVisible();
      await expectNoOverflow(page, 'Observatory (list)', width);
      const list = await (await context.request.get('/api/requests')).json().catch(() => ({ items: [] }));
      for (const item of (list.items || []).slice(0, 3)) { await page.goto(`/observatory?request_id=${item.id}`); await page.waitForTimeout(1200); await expectNoOverflow(page, `Observatory ${item.id}`, width); }
      await context.close();
    });
    test('JudgmentMap', async ({ browser }) => {
      const { context, page } = await as(browser, 'operator', width);
      await page.goto('/judgment-map'); await expect(page.locator('main')).toBeVisible(); await page.waitForTimeout(1200);
      await expectNoOverflow(page, 'JudgmentMap', width);
      await page.goto('/judgment-map?view=list'); await page.waitForTimeout(800);
      await expectNoOverflow(page, 'JudgmentMap (list)', width);
      await context.close();
    });
  });
}
