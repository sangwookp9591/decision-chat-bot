import { expect, test, type Page } from '@playwright/test';

const tenant = process.env.E2E_TENANT || 't-alpha';
const password = process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me';
async function login(page: Page) {
  const response = await page.request.post('/api/auth/login', { data: { email: `requester@${tenant}.dev`, password } });
  expect(response.ok(), `login failed: ${response.status()}`).toBeTruthy();
}

test('live request shows processing stages, saved judgment and evidence panel', async ({ page }) => {
  test.setTimeout(240_000);
  await login(page);
  await page.goto('/');
  await page.getByLabel('요청 내용').fill('사내 회의실 예약 현황을 한곳에서 조회할 수 있는 화면이 필요합니다.');
  await page.getByLabel('파일 첨부').setInputFiles({ name: 'meeting-room-notes.md', mimeType: 'text/markdown', buffer: Buffer.from('회의실 예약 현황을 부서별로 조회합니다. 예약 가능 시간과 담당 부서를 확인할 수 있어야 합니다.') });
  await page.getByRole('button', { name: '요청 보내기' }).click();
  await expect(page.getByRole('heading', { name: '분석 진행' })).toBeVisible();
  await expect(page.locator('.stage-list')).toContainText('내용 정리');
  await expect(page.locator('.stage-list')).toContainText('Jev 판단');
  await expect(page.locator('.stage-list')).toContainText('근거 연결');
  await expect(page.locator('.result-stack:not(.provisional-result)').getByRole('heading', { name: '판단 결과', exact: true })).toBeVisible({ timeout: 180_000 });
  await expect(page.locator('.environment-badge.mode-live').last()).toBeVisible();
  const evidence = page.getByRole('button', { name: /근거 열기|근거 패널 열기/ }).first();
  await expect(evidence).toBeVisible();
  await evidence.click();
  await expect(page.getByRole('heading', { name: '근거 원문' })).toBeVisible();
});

test('live damaged attachment can be excluded before a new revision judgment', async ({ page }) => {
  test.setTimeout(240_000);
  await login(page);
  await page.goto('/');
  await page.getByLabel('요청 내용').fill('분기별 시설 점검 일정을 검색하고 담당자별로 확인하고 싶습니다.');
  await page.getByLabel('파일 첨부').setInputFiles({ name: 'damaged.pdf', mimeType: 'application/pdf', buffer: Buffer.from('not a valid pdf') });
  await page.getByRole('button', { name: '요청 보내기' }).click();
  await expect(page.getByRole('button', { name: /보완 필요|파일 선택 필요|파일 결정 필요/ })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole('group', { name: '읽기 실패 파일' })).toContainText('damaged.pdf');
  await page.getByRole('button', { name: '제외하고 진행' }).click();
  await expect(page.locator('.result-stack:not(.provisional-result)').getByRole('heading', { name: '판단 결과', exact: true })).toBeVisible({ timeout: 180_000 });
  await expect(page.locator('.environment-badge.mode-live').last()).toBeVisible();
  await expect(page.locator('.result-summary > code').filter({ hasText: /revision/ })).toBeVisible();
});
