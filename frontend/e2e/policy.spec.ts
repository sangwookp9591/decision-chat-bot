import { expect, test } from '@playwright/test';

test('validate, publish, inspect history, and rollback policy on live API', async ({ page }) => {
  const login = await page.request.post('/api/auth/login', { data: { email: 'policy_editor@t-alpha.dev', password: process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me' } });
  expect(login.ok(), `login failed: ${login.status()}`).toBeTruthy();
  await page.goto('/policy');
  await expect(page.getByRole('heading', { name: '정책', exact: true })).toBeVisible();
  const configField = page.getByLabel('선택형 판단 최소 확신도');
  const original = await configField.inputValue();
  await configField.fill('{"ai_need": 1.5}');
  await page.getByRole('button', { name: '서버 검증' }).click();
  await expect(page.getByRole('alert')).toContainText('검증 오류');
  await configField.fill(original);
  await page.getByRole('button', { name: '서버 검증' }).click();
  await expect(page.getByText('검증 통과')).toBeVisible();
  await page.getByLabel('게시 사유 (필수)').fill('실제 백엔드 E2E 정책 게시');
  await page.getByRole('button', { name: '게시' }).click();
  await expect(page.getByText(/정책 버전 \d+을 게시했습니다/)).toBeVisible();
  const publishedCount = await page.getByRole('row').count();
  await page.getByRole('button', { name: 'v1', exact: true }).click();
  await expect(page.getByText('v1 diff')).toBeVisible();
  await page.getByLabel('되돌리기 사유 (v1 기준)').fill('실제 백엔드 E2E 되돌리기');
  await page.getByRole('button', { name: '선택 버전 기준으로 되돌리기' }).click();
  await expect(page.getByText(/기준 새 정책 버전 \d+을 만들었습니다/)).toBeVisible();
  await expect.poll(() => page.getByRole('row').count()).toBeGreaterThan(publishedCount);
});
