import { expect, request, test } from '@playwright/test';

const tenant = process.env.E2E_TENANT || 't-alpha';
const password = process.env.ILDONGI_DEV_PASSWORD || 'dev-only-change-me';

async function login(api: import('@playwright/test').APIRequestContext, role: string) {
  const response = await api.post('/api/auth/login', { data: { email: `${role}@${tenant}.dev`, password } });
  expect(response.ok(), `login ${role}: ${response.status()}`).toBeTruthy();
  return (await api.storageState()).cookies.find((cookie) => cookie.name === 'ildongi_csrf')?.value || '';
}

test('labeler confirms three, defers one, and sees a reviewer disagreement', async ({ page }) => {
  test.setTimeout(60_000); // Four persisted decisions plus progress/API checks on both browser engines.
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
  const sample = (id: string) => page.getByRole('heading', { name: new RegExp(id) });
  const confirm = page.getByRole('button', { name: '확정 (Enter)' });
  const toast = page.getByRole('status');
  // The reviewer's vote is listed in Korean; once this labeler confirms a different answer the pair disagrees.
  await expect(sample(candidates[0].id).first()).toBeVisible();
  await expect(page.getByRole('listitem').filter({ hasText: 'reviewer' })).toHaveCount(1);
  // 1) confirm by button (creates the disagreement), 2) change a chip and confirm with Enter after the 1-4 shortcut, 3) confirm again.
  await confirm.click();
  await expect(toast).toContainText('라벨을 확정했습니다.');
  await expect(confirm).toBeEnabled();
  await expect(page.getByText('불일치 · 합의 필요')).toBeVisible();
  await expect(page.getByRole('button', { name: '합의 라벨 확정' })).toBeVisible();
  await page.keyboard.press('j');
  await expect(sample(candidates[1].id).first()).toBeVisible();
  await page.keyboard.press('2');
  const feasibility = page.getByRole('radiogroup', { name: '개발 가능성' });
  await expect(feasibility.getByRole('radio', { checked: true })).toBeFocused();
  await page.keyboard.press('ArrowRight');
  await expect(feasibility.getByRole('radio', { checked: true })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(toast).toContainText('라벨을 확정했습니다.');
  await expect(confirm).toBeEnabled();
  await page.keyboard.press('j');
  await expect(sample(candidates[2].id).first()).toBeVisible();
  await page.keyboard.press('Enter');
  await expect(toast).toContainText('라벨을 확정했습니다.');
  await expect(confirm).toBeEnabled();
  // 4) defer needs a reason.
  await page.keyboard.press('j');
  await expect(sample(candidates[3].id).first()).toBeVisible();
  await page.getByLabel('보류 사유').fill(''); // a rerun starts from the reason saved last time
  await page.getByRole('button', { name: '보류', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('보류 사유를 입력');
  await page.getByLabel('보류 사유').fill('검토 표본 보류');
  await page.getByRole('button', { name: '보류', exact: true }).click();
  await expect(toast).toContainText('보류 사유를 기록했습니다.');
  const progress = await page.request.get('/api/evaluation/candidates?split=tuning');
  const item = (await progress.json()).progress;
  expect(item.confirmed).toBeGreaterThanOrEqual(3);
  expect(item.deferred).toBeGreaterThanOrEqual(1);
  // Saved values keep the API format: strings for choices, arrays for teams and risks.
  const saved = (await (await page.request.get('/api/evaluation/candidates?split=tuning')).json()).candidates[1].my_labels.labels;
  expect(typeof saved.ai_need).toBe('string'); expect(Array.isArray(saved.team_set)).toBe(true); expect(Array.isArray(saved.risk_areas)).toBe(true);
});

test('final split hides predictions; the screen has no JSON text inputs and does not overflow at 375px', async ({ page }) => {
  await login(page.request, 'labeler');
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto('/evaluation');
  await expect(page.getByRole('button', { name: '확정 (Enter)' })).toBeVisible();
  await expect(page.locator('input[type="text"]')).toHaveCount(0);
  for (const tab of ['튜닝', '최종']) {
    await page.getByRole('tab', { name: tab }).click();
    await expect(page.getByRole('tab', { name: tab })).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByRole('button', { name: '확정 (Enter)' })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
  }
  await expect(page.getByText('모델 예측 숨김')).toBeVisible();
  await expect(page.getByText('제안 라벨')).toHaveCount(0);
  await expect(page.getByRole('button', { name: '확정 (Enter)' })).toBeDisabled();
});
