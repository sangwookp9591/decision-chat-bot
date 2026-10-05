import { expect, test, type Page } from '@playwright/test';
import { mkdir } from 'node:fs/promises';

const tenant = process.env.E2E_TENANT || 't-rem-ui';
const password = process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me';
const requestId = process.env.REM_UI_REQUEST_ID || 'req_rem_ui';
const shots = new URL('../../artifacts/review/rem-ui/', import.meta.url).pathname;

async function login(page: Page, email: string) {
  const response = await page.request.post('/api/auth/login', { data: { email, password } });
  expect(response.ok(), `login ${email}: ${response.status()}`).toBeTruthy();
}

test('review queue title and masked detail respect source permission', async ({ page }, testInfo) => {
  await mkdir(shots, { recursive: true });
  await login(page, `reviewer@${tenant}.dev`);
  const reviewsLoaded = page.waitForResponse((response) => response.url().includes('/api/reviews?status=pending'));
  await page.goto('/review');
  await reviewsLoaded;
  const row = page.locator('.review-layout nav button').filter({ hasText: '회의실 예약 자동화' }).first();
  test.skip(await row.count() === 0, `rem-ui 제목 fixture가 없음: ${tenant} tenant의 '회의실 예약 자동화' 요청을 준비해야 함`);
  await expect(row.locator('.review-row-title')).toHaveText('회의실 예약 자동화');
  await page.screenshot({ path: `${shots}/${testInfo.project.name}-review-list.png`, fullPage: true });
  await row.click();
  await expect(page.getByRole('heading', { name: '회의실 예약 자동화' })).toBeVisible();
  await expect(page.getByText(/원문 열람 권한이 없습니다/)).toBeVisible();
  await expect(page.getByText(/허용된 마스킹 요약만 표시합니다/)).toBeVisible();
  await expect(row.locator('.review-row-title')).toHaveText('회의실 예약 자동화');
  await page.screenshot({ path: `${shots}/${testInfo.project.name}-review-detail.png`, fullPage: true });
});

test('source-reading reviewer can see the submitted text in review detail', async ({ page }, testInfo) => {
  await mkdir(shots, { recursive: true });
  await login(page, `source_reader@${tenant}.dev`);
  const reviewsLoaded = page.waitForResponse((response) => response.url().includes('/api/reviews?status=pending'));
  await page.goto('/review');
  await reviewsLoaded;
  const row = page.locator('.review-layout nav button').filter({ hasText: '회의실 예약 자동화' }).first();
  test.skip(await row.count() === 0, `rem-ui 원문 fixture가 없음: ${tenant} tenant의 '회의실 예약 자동화' 요청을 준비해야 함`);
  await row.click();
  await expect(page.getByText('업무 판단 요청')).toBeVisible();
  await expect(page.getByText(/원문 열람 권한이 없습니다/)).toHaveCount(0);
  await page.screenshot({ path: `${shots}/${testInfo.project.name}-review-source-reader.png`, fullPage: true });
});

test('source reader sees the original and result identifiers stay compact', async ({ page }, testInfo) => {
  await mkdir(shots, { recursive: true });
  await login(page, `requester@${tenant}.dev`);
  const fixture = await page.request.get(`/api/requests/${requestId}`);
  test.skip(!fixture.ok(), `REM_UI_REQUEST_ID=${requestId} fixture가 없음 (HTTP ${fixture.status()})`);
  await page.goto(`/?request_id=${requestId}`);
  test.skip(await page.getByRole('heading', { name: '판단 결과' }).count() === 0, `REM_UI_REQUEST_ID=${requestId} fixture가 없거나 결과가 없음`);
  await expect(page.getByRole('heading', { name: '판단 결과' })).toBeVisible();
  const summary = page.locator('.result-stack').first();
  await expect(summary.locator('.result-ids')).toBeHidden();
  await page.screenshot({ path: `${shots}/${testInfo.project.name}-result-card.png`, fullPage: true });
  await page.getByRole('button', { name: '자세히 보기' }).last().click();
  await expect(page.locator('.result-ids')).toBeVisible();
  await expect(page.locator('.result-ids code.short-id')).toHaveCount(2);
  await page.screenshot({ path: `${shots}/${testInfo.project.name}-result-detail.png`, fullPage: true });
});
