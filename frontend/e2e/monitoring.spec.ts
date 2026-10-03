import { expect, test } from '@playwright/test';

test('operator monitoring screen matches a real API aggregate', async ({ page }) => {
  const login = await page.request.post('/api/auth/login', { data: { email: 'operator@t-alpha.dev', password: process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me' } });
  expect(login.ok(), `login failed: ${login.status()}`).toBeTruthy();
  const response = await page.request.get('/api/monitoring/summary');
  expect(response.ok(), `summary failed: ${response.status()}`).toBeTruthy();
  const actual = await response.json();
  await page.goto('/monitoring');
  await expect(page.getByRole('heading', { name: '모니터링' })).toBeVisible();
  const expected = String(actual.requests.received + actual.requests.failed_before_id);
  const requestsCard = page.locator('.monitor-kpis article').filter({ hasText: '요청 수' });
  await expect(requestsCard.locator('strong')).toHaveText(expected);
});
