import { expect, test } from '@playwright/test';

// Live scenario for docs/architecture/PROGRESSIVE_RESULTS.md (needs API + worker; use a dedicated tenant's account).
// Records when each area first appears (performance.now() inside the page) so TTFT-style numbers land in the report.
const email = process.env.E2E_REQUESTER || 'requester@t-alpha.dev';
test.use({ video: 'on' });

test('submit → optimistic bubble → provisional cards → final result, with measured timings', async ({ page }, info) => {
  const login = await page.request.post('/api/auth/login', { data: { email, password: process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me' } });
  expect(login.ok(), `login failed: ${login.status()}`).toBeTruthy();
  await page.goto('/');
  await page.evaluate(() => {
    const marks: Record<string, number> = {};
    (window as unknown as { __marks: typeof marks }).__marks = marks;
    const seen = () => {
      const now = performance.now();
      if (!marks.optimistic && document.querySelector('[aria-label="내가 보낸 요청"]')) marks.optimistic = now;
      if (!marks.provisional && document.querySelector('.provisional-badge')) marks.provisional = now;
      if (!marks.final && [...document.querySelectorAll('.result-summary h2')].some((h) => h.textContent === '판단 결과')) marks.final = now;
    };
    new MutationObserver(seen).observe(document.body, { childList: true, subtree: true, characterData: true });
  });
  await page.getByLabel('요청 내용').fill('고객 문의 분류에 챗봇을 도입하고 싶습니다. 긴급하지 않고 AI팀이 주관하면 좋겠습니다.');
  const clickedAt = await page.evaluate(() => performance.now());
  await page.getByRole('button', { name: '요청 보내기' }).click();
  await expect(page.getByRole('group', { name: '내가 보낸 요청' })).toBeVisible({ timeout: 2000 });
  await expect(page.locator('.result-stack:not(.provisional-result)').getByRole('heading', { name: '판단 결과', exact: true })).toBeVisible({ timeout: 120_000 });
  const marks = await page.evaluate(() => (window as unknown as { __marks: Record<string, number> }).__marks);
  const rel = (value?: number) => (value === undefined ? null : Math.round(value - clickedAt));
  const timings = { click_to_optimistic_ms: rel(marks.optimistic), click_to_provisional_ms: rel(marks.provisional), click_to_final_ms: rel(marks.final) };
  info.annotations.push({ type: 'timings', description: JSON.stringify(timings) });
  console.log('PROGRESSIVE_TIMINGS', JSON.stringify(timings));
  expect(timings.click_to_optimistic_ms).not.toBeNull();
  expect(timings.click_to_optimistic_ms!).toBeLessThan(1000);
  if (process.env.E2E_REQUIRE_PARTIAL) { expect(timings.click_to_provisional_ms).not.toBeNull(); expect(timings.click_to_provisional_ms!).toBeLessThan(timings.click_to_final_ms!); }
  // After the final judgment the provisional markers are gone.
  await expect(page.locator('.provisional-badge')).toHaveCount(0);
});
