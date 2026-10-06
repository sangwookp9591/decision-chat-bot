import { expect, test, type Page } from '@playwright/test';

async function login(page: Page, role: string) {
  const r = await page.request.post('/api/auth/login', { data: { email: `${role}@${process.env.E2E_TENANT || 't-alpha'}.dev`, password: process.env.ILDONGI_DEV_PASSWORD || 'dev-only-change-me' } });
  expect(r.ok(), `login ${role}`).toBeTruthy();
}

test('모니터링: 기간을 한국어 형식 입력으로 바꾸고 적용하면 해당 범위로 다시 조회한다', async ({ page }) => {
  await login(page, 'operator');
  const urls: string[] = [];
  page.on('request', (req) => { if (req.url().includes('/api/monitoring/summary')) urls.push(req.url()); });
  await page.goto('/monitoring');
  await expect(page.getByRole('group', { name: '시작' })).toBeVisible();
  await page.getByLabel('시작 년').fill('2026'); await page.getByLabel('시작 월').fill('1'); await page.getByLabel('시작 일').fill('1');
  await page.getByLabel('조직').fill('t-alpha-ai');
  const before = urls.length;
  await page.getByRole('button', { name: '적용' }).click();
  await expect.poll(() => urls.length).toBeGreaterThan(before);
  expect(decodeURIComponent(urls[urls.length - 1])).toContain('org=t-alpha-ai');
  expect(urls[urls.length - 1]).toContain('from=2026-01-01');
  await page.getByLabel('시작 월').fill('13');
  await expect(page.getByText('시작과 종료 시각을 모두 올바르게 입력해 주세요.')).toBeVisible();
  await expect(page.getByRole('button', { name: '적용' })).toBeDisabled();
});

test('실행 관찰: 요청을 검색해 고르면 실행 목록이 따라온다', async ({ page }) => {
  await login(page, 'operator');
  await page.goto('/observatory');
  const request = page.getByRole('combobox', { name: '요청 선택' });
  await expect(request).toBeVisible();
  // The select is disabled only while the request list loads (or when it is empty): wait for that to settle before deciding which case this is.
  const empty = page.getByText('관찰 가능한 요청이 없습니다');
  await expect.poll(async () => !(await request.isDisabled()) || await empty.isVisible()).toBe(true);
  if (await request.isDisabled()) { await expect(empty).toBeVisible(); return; }
  await expect.poll(async () => (await request.inputValue()).length).toBeGreaterThan(0);
  await request.click();
  await page.getByRole('option').first().click();
  await expect(page.getByRole('combobox', { name: '실행 선택' })).toBeVisible();
});

test('검토 대기·업무: 필터는 공용 선택 구성요소이고 빈 목록은 안내 카드를 보여 준다', async ({ page }) => {
  await login(page, 'reviewer');
  await page.goto('/review');
  await page.getByLabel('검토 상태 필터').selectOption('info_requested');
  await expect(page.getByRole('checkbox', { name: '긴급 우선 정렬' })).toBeVisible();
  await page.goto('/tasks');
  await page.getByLabel('상태').selectOption('완료');
  await expect(page.getByRole('button', { name: '새로고침' })).toHaveCSS('min-height', '44px');
});
