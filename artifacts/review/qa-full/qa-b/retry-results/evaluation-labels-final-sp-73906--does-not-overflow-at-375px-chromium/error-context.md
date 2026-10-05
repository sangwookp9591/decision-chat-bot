# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: evaluation-labels.spec.ts >> final split hides predictions; the screen has no JSON text inputs and does not overflow at 375px
- Location: e2e/evaluation-labels.spec.ts:74:1

# Error details

```
TimeoutError: apiRequestContext.post: Timeout 15000ms exceeded.
Call log:
  - → POST http://127.0.0.1:8791/api/auth/login
    - user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.8010.12 Safari/537.36
    - accept: */*
    - accept-encoding: gzip,deflate,br
    - content-type: application/json
    - content-length: 73

```

# Test source

```ts
  1  | import { expect, request, test } from '@playwright/test';
  2  | 
  3  | const tenant = process.env.E2E_TENANT || 't-alpha';
  4  | const password = process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me';
  5  | 
  6  | async function login(api: import('@playwright/test').APIRequestContext, role: string) {
> 7  |   const response = await api.post('/api/auth/login', { data: { email: `${role}@${tenant}.dev`, password } });
     |                              ^ TimeoutError: apiRequestContext.post: Timeout 15000ms exceeded.
  8  |   expect(response.ok(), `login ${role}: ${response.status()}`).toBeTruthy();
  9  |   return (await api.storageState()).cookies.find((cookie) => cookie.name === 'jev_csrf')?.value || '';
  10 | }
  11 | 
  12 | test('labeler confirms three, defers one, and sees a reviewer disagreement', async ({ page }) => {
  13 |   await login(page.request, 'labeler');
  14 |   const reviewer = await request.newContext();
  15 |   const reviewerCsrf = await login(reviewer, 'reviewer');
  16 |   const list = await page.request.get('/api/evaluation/candidates?split=tuning');
  17 |   expect(list.ok()).toBeTruthy();
  18 |   const candidates = (await list.json()).candidates as Array<{ id: string; proposed_labels: Record<string, unknown> }>;
  19 |   expect(candidates.length).toBeGreaterThanOrEqual(4);
  20 |   const first = candidates[0];
  21 |   const otherLabels = { ...first.proposed_labels, ai_need: first.proposed_labels.ai_need === '필요' ? '불필요' : '필요' };
  22 |   const vote = await reviewer.put(`/api/evaluation/candidates/tuning/${first.id}`, {
  23 |     headers: { 'X-CSRF-Token': reviewerCsrf }, data: { labels: otherLabels, confidence: 0.8, status: 'confirmed' },
  24 |   });
  25 |   expect(vote.ok()).toBeTruthy();
  26 |   await reviewer.dispose();
  27 |   await page.goto('/evaluation');
  28 |   await expect(page.getByRole('heading', { name: '평가 정답 확정' })).toBeVisible();
  29 |   const sample = (id: string) => page.getByRole('heading', { name: new RegExp(id) });
  30 |   const confirm = page.getByRole('button', { name: '확정 (Enter)' });
  31 |   const toast = page.getByRole('status');
  32 |   // The reviewer's vote is listed in Korean; once this labeler confirms a different answer the pair disagrees.
  33 |   await expect(sample(candidates[0].id).first()).toBeVisible();
  34 |   await expect(page.getByRole('listitem').filter({ hasText: 'reviewer' })).toHaveCount(1);
  35 |   // 1) confirm by button (creates the disagreement), 2) change a chip and confirm with Enter after the 1-4 shortcut, 3) confirm again.
  36 |   await confirm.click();
  37 |   await expect(toast).toContainText('라벨을 확정했습니다.');
  38 |   await expect(confirm).toBeEnabled();
  39 |   await expect(page.getByText('불일치 · 합의 필요')).toBeVisible();
  40 |   await expect(page.getByRole('button', { name: '합의 라벨 확정' })).toBeVisible();
  41 |   await page.keyboard.press('j');
  42 |   await expect(sample(candidates[1].id).first()).toBeVisible();
  43 |   await page.keyboard.press('2');
  44 |   const feasibility = page.getByRole('radiogroup', { name: '개발 가능성' });
  45 |   await expect(feasibility.getByRole('radio', { checked: true })).toBeFocused();
  46 |   await page.keyboard.press('ArrowRight');
  47 |   await expect(feasibility.getByRole('radio', { checked: true })).toBeFocused();
  48 |   await page.keyboard.press('Enter');
  49 |   await expect(toast).toContainText('라벨을 확정했습니다.');
  50 |   await expect(confirm).toBeEnabled();
  51 |   await page.keyboard.press('j');
  52 |   await expect(sample(candidates[2].id).first()).toBeVisible();
  53 |   await page.keyboard.press('Enter');
  54 |   await expect(toast).toContainText('라벨을 확정했습니다.');
  55 |   await expect(confirm).toBeEnabled();
  56 |   // 4) defer needs a reason.
  57 |   await page.keyboard.press('j');
  58 |   await expect(sample(candidates[3].id).first()).toBeVisible();
  59 |   await page.getByLabel('보류 사유').fill(''); // a rerun starts from the reason saved last time
  60 |   await page.getByRole('button', { name: '보류', exact: true }).click();
  61 |   await expect(page.getByRole('alert')).toContainText('보류 사유를 입력');
  62 |   await page.getByLabel('보류 사유').fill('검토 표본 보류');
  63 |   await page.getByRole('button', { name: '보류', exact: true }).click();
  64 |   await expect(toast).toContainText('보류 사유를 기록했습니다.');
  65 |   const progress = await page.request.get('/api/evaluation/candidates?split=tuning');
  66 |   const item = (await progress.json()).progress;
  67 |   expect(item.confirmed).toBeGreaterThanOrEqual(3);
  68 |   expect(item.deferred).toBeGreaterThanOrEqual(1);
  69 |   // Saved values keep the API format: strings for choices, arrays for teams and risks.
  70 |   const saved = (await (await page.request.get('/api/evaluation/candidates?split=tuning')).json()).candidates[1].my_labels.labels;
  71 |   expect(typeof saved.ai_need).toBe('string'); expect(Array.isArray(saved.team_set)).toBe(true); expect(Array.isArray(saved.risk_areas)).toBe(true);
  72 | });
  73 | 
  74 | test('final split hides predictions; the screen has no JSON text inputs and does not overflow at 375px', async ({ page }) => {
  75 |   await login(page.request, 'labeler');
  76 |   await page.setViewportSize({ width: 375, height: 800 });
  77 |   await page.goto('/evaluation');
  78 |   await expect(page.getByRole('button', { name: '확정 (Enter)' })).toBeVisible();
  79 |   await expect(page.locator('input[type="text"]')).toHaveCount(0);
  80 |   for (const tab of ['튜닝', '최종']) {
  81 |     await page.getByRole('tab', { name: tab }).click();
  82 |     await expect(page.getByRole('tab', { name: tab })).toHaveAttribute('aria-selected', 'true');
  83 |     await expect(page.getByRole('button', { name: '확정 (Enter)' })).toBeVisible();
  84 |     expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
  85 |   }
  86 |   await expect(page.getByText('모델 예측 숨김')).toBeVisible();
  87 |   await expect(page.getByText('제안 라벨')).toHaveCount(0);
  88 |   await expect(page.getByRole('button', { name: '확정 (Enter)' })).toBeDisabled();
  89 | });
  90 | 
```