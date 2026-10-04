import { expect, request, test } from '@playwright/test';

const tenant = process.env.E2E_TENANT || 't-alpha';
const password = process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me';

async function login(api: import('@playwright/test').APIRequestContext, role: string) {
  const response = await api.post('/api/auth/login', { data: { email: `${role}@${tenant}.dev`, password } });
  expect(response.ok(), `login ${role}: ${response.status()}`).toBeTruthy();
  return (await api.storageState()).cookies.find((cookie) => cookie.name === 'jev_csrf')?.value || '';
}

test('labeler confirms three, defers one, and sees a reviewer disagreement', async ({ page }) => {
  await login(page.request, 'labeler');
  const reviewer = await request.newContext();
  const reviewerCsrf = await login(reviewer, 'reviewer');
  const list = await page.request.get('/api/evaluation/candidates?split=tuning');
  expect(list.ok()).toBeTruthy();
  const candidates = (await list.json()).candidates as Array<{ id: string; proposed_labels: Record<string, unknown> }>;
  expect(candidates.length).toBeGreaterThanOrEqual(4);
  const first = candidates[0];
  const otherLabels = { ...first.proposed_labels, ai_need: first.proposed_labels.ai_need === '필요' ? '불필요' : '필요' };
  const vote = await reviewer.put(`/api/evaluation/candidates/tuning/${first.id}`, {
    headers: { 'X-CSRF-Token': reviewerCsrf }, data: { labels: otherLabels, confidence: 0.8, status: 'confirmed' },
  });
  expect(vote.ok()).toBeTruthy();
  await reviewer.dispose();
  await page.goto('/evaluation');
  await expect(page.getByRole('heading', { name: '평가 정답 확정' })).toBeVisible();
  for (let index = 0; index < 4; index += 1) {
    const candidate = candidates[index];
    await expect(page.getByRole('heading', { name: candidate.id })).toBeVisible();
    if (index === 3) {
      await page.getByLabel('보류 사유').fill('검토 표본 보류');
      await page.getByRole('button', { name: '보류', exact: true }).click();
    } else {
      await page.getByRole('button', { name: '확정 (Enter)' }).click();
      }
    if (index < 3) await page.keyboard.press('j');
  }
  await expect(page.getByRole('status')).toContainText('보류 사유를 기록했습니다.');
  const progress = await page.request.get('/api/evaluation/candidates?split=tuning');
  const item = (await progress.json()).progress;
  expect(item.confirmed).toBeGreaterThanOrEqual(3);
  expect(item.deferred).toBeGreaterThanOrEqual(1);
});
