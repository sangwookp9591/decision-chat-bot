# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: rem-ui.spec.ts >> review queue title and masked detail respect source permission
- Location: artifacts/review/completeness/scratch/suite/rem-ui.spec.ts:14:5

# Error details

```
Error: expect(locator).toHaveText(expected) failed

Locator: locator('.review-layout nav button').filter({ hasText: '회의실 예약 자동화' }).first().locator('.review-row-title')
Expected: "회의실 예약 자동화"
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toHaveText" locator('.review-layout nav button').filter({ hasText: '회의실 예약 자동화' }).first().locator('.review-row-title') with timeout 5000ms
  - waiting for locator('.review-layout nav button').filter({ hasText: '회의실 예약 자동화' }).first().locator('.review-row-title')

```

```yaml
- complementary:
  - text: Jev Triage
  - navigation "주 메뉴":
    - link "요청 접수":
      - /url: /
    - link "검토 대기":
      - /url: /review
    - link "업무":
      - /url: /tasks
    - link "실행 관찰":
      - /url: /observatory
    - link "판단 맵":
      - /url: /judgment-map
    - link "규칙 학습":
      - /url: /learning
    - link "모니터링":
      - /url: /monitoring
    - link "정책":
      - /url: /policy
    - link "평가 라벨":
      - /url: /evaluation
  - strong: usr_t-audit-e2e-1005_reviewer
  - text: 검토자
  - button "로그아웃"
- banner:
  - text: 의사결정 지원 usr_t-audit-e2e-1005_reviewer · 검토자 live
  - button "로그아웃"
- main:
  - paragraph: 사람 검토
  - heading "검토 대기" [level=1]
  - paragraph: 사유와 긴급 신호를 확인하고 원안에 대한 결정을 기록합니다.
  - button "새로고침"
  - navigation "검토 대기 목록":
    - heading "대기 1건" [level=2]
    - text: 상태
    - combobox "검토 상태 필터":
      - option "대기" [selected]
      - option "승인"
      - option "반려"
      - option "정보 요청"
    - checkbox "긴급 우선 정렬"
    - text: 긴급 우선 정렬
    - 'button "분기별 시설 점검 일정을 검색하고 담당자별로 확인하고 싶습니다. 일반 req_33a60302a76c4b96906b01cdf11aab4e 대기 근거 미완료 · 개발 가능성 미충족 · 분류 미확정: 개발 가능성 · 선택 확신도 미충족: 긴급도 · 선택 확신도 미충족: 담당 조직 · 주관 · 참여 여부 불확실: IT팀 참여 확률 · 참여 여부 불확실: 현업 참여 확률 · 업무 책임 또는 산출물 누락 · 정책에서 자동 배정 비허용 검토 조직 IT팀 · 14분 대기"':
      - strong: 분기별 시설 점검 일정을 검색하고 담당자별로 확인하고 싶습니다.
      - text: 일반
      - code: req_33a60302a76c4b96906b01cdf11aab4e
      - text: "대기 근거 미완료 · 개발 가능성 미충족 · 분류 미확정: 개발 가능성 · 선택 확신도 미충족: 긴급도 · 선택 확신도 미충족: 담당 조직 · 주관 · 참여 여부 불확실: IT팀 참여 확률 · 참여 여부 불확실: 현업 참여 확률 · 업무 책임 또는 산출물 누락 · 정책에서 자동 배정 비허용 검토 조직 IT팀 · 14분 대기"
  - article:
    - paragraph: 왼쪽 목록에서 요청을 선택하세요.
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
> 19 |   await expect(row.locator('.review-row-title')).toHaveText('회의실 예약 자동화');
     |                                                  ^ Error: expect(locator).toHaveText(expected) failed
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
  33 |   await page.locator('.review-layout nav button').filter({ hasText: '회의실 예약 자동화' }).first().click();
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