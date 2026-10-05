# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: rem-ui.spec.ts >> source-reading reviewer can see the submitted text in review detail
- Location: artifacts/review/completeness/scratch/suite/rem-ui.spec.ts:29:5

# Error details

```
Test timeout of 60000ms exceeded.
```

```
Error: locator.click: Test timeout of 60000ms exceeded.
Call log:
  - waiting for locator('.review-layout nav button').filter({ hasText: '회의실 예약 자동화' }).first()

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - complementary [ref=e4]:
    - generic [ref=e5]: Jev Triage
    - navigation "주 메뉴" [ref=e6]:
      - link "요청 접수" [ref=e7] [cursor=pointer]:
        - /url: /
      - link "검토 대기" [ref=e8] [cursor=pointer]:
        - /url: /review
      - link "업무" [ref=e9] [cursor=pointer]:
        - /url: /tasks
      - link "실행 관찰" [ref=e10] [cursor=pointer]:
        - /url: /observatory
      - link "판단 맵" [ref=e11] [cursor=pointer]:
        - /url: /judgment-map
      - link "규칙 학습" [ref=e12] [cursor=pointer]:
        - /url: /learning
      - link "모니터링" [ref=e13] [cursor=pointer]:
        - /url: /monitoring
      - link "정책" [ref=e14] [cursor=pointer]:
        - /url: /policy
      - link "평가 라벨" [ref=e15] [cursor=pointer]:
        - /url: /evaluation
    - generic [ref=e16]:
      - strong [ref=e17]: usr_t-audit-e2e-1005_source_reader
      - generic [ref=e18]: 요청자 · 검토자
      - button "로그아웃" [ref=e19] [cursor=pointer]
  - generic [ref=e20]:
    - banner [ref=e21]:
      - generic [ref=e22]: 의사결정 지원
      - generic [ref=e23]:
        - generic [ref=e24]: usr_t-audit-e2e-1005_source_reader · 요청자 · 검토자
        - generic [ref=e25]: live
        - button "로그아웃" [ref=e26] [cursor=pointer]
    - main [ref=e27]:
      - generic [ref=e28]:
        - generic [ref=e29]:
          - generic [ref=e30]:
            - paragraph [ref=e31]: 사람 검토
            - heading "검토 대기" [level=1] [ref=e32]
            - paragraph [ref=e33]: 사유와 긴급 신호를 확인하고 원안에 대한 결정을 기록합니다.
          - button "새로고침" [ref=e34] [cursor=pointer]
        - generic [ref=e35]:
          - navigation "검토 대기 목록" [ref=e36]:
            - heading "대기 0건" [level=2] [ref=e37]
            - generic [ref=e38]:
              - generic [ref=e39]: 상태
              - combobox "검토 상태 필터" [ref=e41]:
                - option "대기" [selected]
                - option "승인"
                - option "반려"
                - option "정보 요청"
            - generic [ref=e42] [cursor=pointer]:
              - checkbox "긴급 우선 정렬" [ref=e43]
              - generic [ref=e45]: 긴급 우선 정렬
            - generic [ref=e46]:
              - generic [aria-hidden] [ref=e47]: ◇
              - strong [ref=e48]: 대기 중인 검토가 없습니다
              - paragraph [ref=e49]: 사람 검토가 필요한 요청이 생기면 긴급도·사유·대기 시간과 함께 이곳에 나타납니다.
          - article [ref=e50]:
            - paragraph [ref=e51]: 왼쪽 목록에서 요청을 선택하세요.
```

# Test source

```ts
  1  | import { expect, test, type Page } from '@playwright/test';
  2  | import { mkdir } from 'node:fs/promises';
  3  | 
  4  | const tenant = process.env.E2E_TENANT || 't-rem-ui';
  5  | const password = process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me';
  6  | const requestId = process.env.REM_UI_REQUEST_ID || 'req_rem_ui';
  7  | const shots = '/Users/psw/Projects/decision-chat-bot/artifacts/review/completeness/e2e/rem-ui';
  8  | 
  9  | async function login(page: Page, email: string) {
  10 |   const response = await page.request.post('/api/auth/login', { data: { email, password } });
  11 |   expect(response.ok(), `login ${email}: ${response.status()}`).toBeTruthy();
  12 | }
  13 | 
  14 | test('review queue title and masked detail respect source permission', async ({ page }, testInfo) => {
  15 |   await mkdir(shots, { recursive: true });
  16 |   await login(page, `reviewer@${tenant}.dev`);
  17 |   await page.goto('/review');
  18 |   const row = page.locator('.review-layout nav button').filter({ hasText: '회의실 예약 자동화' }).first();
  19 |   await expect(row.locator('.review-row-title')).toHaveText('회의실 예약 자동화');
  20 |   await page.screenshot({ path: `${shots}/${testInfo.project.name}-review-list.png`, fullPage: true });
  21 |   await row.click();
  22 |   await expect(page.getByRole('heading', { name: '회의실 예약 자동화' })).toBeVisible();
  23 |   await expect(page.getByText(/원문 열람 권한이 없습니다/)).toBeVisible();
  24 |   await expect(page.getByText(/허용된 마스킹 요약만 표시합니다/)).toBeVisible();
  25 |   await expect(row.locator('.review-row-title')).toHaveText('회의실 예약 자동화');
  26 |   await page.screenshot({ path: `${shots}/${testInfo.project.name}-review-detail.png`, fullPage: true });
  27 | });
  28 | 
  29 | test('source-reading reviewer can see the submitted text in review detail', async ({ page }, testInfo) => {
  30 |   await mkdir(shots, { recursive: true });
  31 |   await login(page, `source_reader@${tenant}.dev`);
  32 |   await page.goto('/review');
> 33 |   await page.locator('.review-layout nav button').filter({ hasText: '회의실 예약 자동화' }).first().click();
     |                                                                                             ^ Error: locator.click: Test timeout of 60000ms exceeded.
  34 |   await expect(page.getByText('업무 판단 요청')).toBeVisible();
  35 |   await expect(page.getByText(/원문 열람 권한이 없습니다/)).toHaveCount(0);
  36 |   await page.screenshot({ path: `${shots}/${testInfo.project.name}-review-source-reader.png`, fullPage: true });
  37 | });
  38 | 
  39 | test('source reader sees the original and result identifiers stay compact', async ({ page }, testInfo) => {
  40 |   await mkdir(shots, { recursive: true });
  41 |   await login(page, `requester@${tenant}.dev`);
  42 |   await page.goto(`/?request_id=${requestId}`);
  43 |   await expect(page.getByRole('heading', { name: '판단 결과' })).toBeVisible();
  44 |   const summary = page.locator('.result-stack').first();
  45 |   await expect(summary.locator('.result-ids')).toBeHidden();
  46 |   await page.screenshot({ path: `${shots}/${testInfo.project.name}-result-card.png`, fullPage: true });
  47 |   await page.getByRole('button', { name: '자세히 보기' }).last().click();
  48 |   await expect(page.locator('.result-ids')).toBeVisible();
  49 |   await expect(page.locator('.result-ids code.short-id')).toHaveCount(2);
  50 |   await page.screenshot({ path: `${shots}/${testInfo.project.name}-result-detail.png`, fullPage: true });
  51 | });
  52 | 
```