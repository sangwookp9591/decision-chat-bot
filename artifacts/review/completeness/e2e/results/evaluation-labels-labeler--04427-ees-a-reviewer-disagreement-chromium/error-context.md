# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: evaluation-labels.spec.ts >> labeler confirms three, defers one, and sees a reviewer disagreement
- Location: ../artifacts/review/completeness/scratch/suite/evaluation-labels.spec.ts:12:5

# Error details

```
Error: expect(received).toBeGreaterThanOrEqual(expected)

Expected: >= 3
Received:    2
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
      - strong [ref=e17]: usr_t-audit-e2e-1005_labeler
      - generic [ref=e18]: labeler
      - button "로그아웃" [ref=e19] [cursor=pointer]
  - generic [ref=e20]:
    - banner [ref=e21]:
      - generic [ref=e22]: 의사결정 지원
      - generic [ref=e23]:
        - generic [ref=e24]: usr_t-audit-e2e-1005_labeler · labeler
        - generic [ref=e25]: live
        - button "로그아웃" [ref=e26] [cursor=pointer]
    - main [ref=e27]:
      - generic [ref=e28]:
        - paragraph [ref=e29]: 정답 라벨
        - heading "평가 정답 확정" [level=1] [ref=e30]
        - generic [ref=e31]:
          - generic [ref=e32]:
            - tablist "분할 선택" [ref=e33]:
              - tab "튜닝" [selected] [ref=e34] [cursor=pointer]
              - tab "최종" [ref=e35] [cursor=pointer]
            - group "표본 이동" [ref=e36]:
              - button "이전 표본" [ref=e37] [cursor=pointer]: ‹
              - generic [ref=e38]:
                - strong [ref=e39]: "4"
                - text: / 60
              - button "다음 표본" [ref=e40] [cursor=pointer]: ›
          - generic "진행률" [ref=e41]:
            - generic [ref=e42]:
              - generic [ref=e43]: 2 확정
              - generic [ref=e44]: 1 보류
              - generic [ref=e45]: 57 남음
              - generic [ref=e46]: 3% 완료
            - progressbar "확정 진행률" [ref=e47]
        - generic [ref=e50]:
          - region [ref=e51]:
            - generic [ref=e52]:
              - heading "표본 pharma-004" [level=2] [ref=e53]
              - generic [ref=e54]:
                - generic [aria-hidden] [ref=e55]: ♙
                - text: 내 결정 · 보류
            - paragraph [ref=e56]: 업무를 개선하고 싶습니다. 현재 대상 데이터와 기대 결과는 정리되지 않았습니다. 필요한 비식별 표본과 담당 부서의 검토 시간이 확보되어 있습니다. 이번 주 안에 초기 대응 여부를 정해야 합니다.
            - generic [ref=e57]:
              - heading "제안 라벨" [level=3] [ref=e58]
              - generic [ref=e59]:
                - generic [ref=e60]:
                  - term [ref=e61]: AI 필요성
                  - definition [ref=e62]:
                    - generic [ref=e63]: 정보 부족
                - generic [ref=e64]:
                  - term [ref=e65]: 개발 가능성
                  - definition [ref=e66]:
                    - generic [ref=e67]: 가능
                - generic [ref=e68]:
                  - term [ref=e69]: 긴급도
                  - definition [ref=e70]:
                    - generic [ref=e71]: 긴급
                - generic [ref=e72]:
                  - term [ref=e73]: 참여 팀 구성
                  - definition [ref=e74]:
                    - generic [ref=e75]: 현업
                - generic [ref=e76]:
                  - term [ref=e77]: 위험 영역
                  - definition [ref=e78]:
                    - generic [ref=e79]: 없음
              - group [ref=e80]:
                - generic "기술 상세" [ref=e81] [cursor=pointer]
            - generic [ref=e82]:
              - heading "근거 메모" [level=3] [ref=e83]
              - paragraph [ref=e84]: 요청은 정보 부족 성격으로 제안했고, 실행 전제와 일정 설명을 고려해 가능·긴급로 분류했습니다.
            - generic [ref=e85]:
              - heading "합의 상태" [level=3] [ref=e86]
              - paragraph [ref=e87]:
                - generic [ref=e88]:
                  - generic [aria-hidden] [ref=e89]: ○
                  - text: 라벨 없음
                - generic [ref=e90]: 아직 라벨 없음
              - group [ref=e91]:
                - generic "기술 상세" [ref=e92] [cursor=pointer]
            - generic [ref=e93]:
              - heading "다른 라벨러 이력 1건" [level=3] [ref=e94]:
                - text: 다른 라벨러 이력
                - generic [ref=e95]: 1건
              - list [ref=e96]:
                - listitem [ref=e97]:
                  - generic [ref=e98]:
                    - strong [ref=e99]: usr_t-audit-e2e-1005_labeler (나)
                    - generic [ref=e100]:
                      - generic [aria-hidden] [ref=e101]: ♙
                      - text: 보류
                    - time [ref=e102]: 26. 10. 5. 오후 12:23
                  - generic [ref=e103]:
                    - generic [ref=e104]:
                      - term [ref=e105]: AI 필요성
                      - definition [ref=e106]:
                        - generic [ref=e107]: 정보 부족
                    - generic [ref=e108]:
                      - term [ref=e109]: 개발 가능성
                      - definition [ref=e110]:
                        - generic [ref=e111]: 가능
                    - generic [ref=e112]:
                      - term [ref=e113]: 긴급도
                      - definition [ref=e114]:
                        - generic [ref=e115]: 긴급
                    - generic [ref=e116]:
                      - term [ref=e117]: 참여 팀 구성
                      - definition [ref=e118]:
                        - generic [ref=e119]: 현업
                    - generic [ref=e120]:
                      - term [ref=e121]: 위험 영역
                      - definition [ref=e122]:
                        - generic [ref=e123]: 없음
                  - paragraph [ref=e124]: "보류 사유: 검토 표본 보류"
          - region [ref=e125]:
            - generic [ref=e126]:
              - heading "정답 입력" [level=2] [ref=e127]
              - generic [ref=e128]: 숫자 1–4로 항목 이동
            - radiogroup "AI 필요성" [ref=e129]:
              - generic [ref=e131]:
                - generic [aria-hidden] [ref=e132]: "1"
                - generic [ref=e133]: AI 필요성
              - paragraph [ref=e134]: AI가 필요한 요청인지 (필요·불필요·혼합)
              - generic [ref=e135]:
                - generic [ref=e136]:
                  - radio "필요" [ref=e137] [cursor=pointer]
                  - radio "불필요" [ref=e138] [cursor=pointer]
                  - radio "혼합" [ref=e139] [cursor=pointer]
                - radio "정보 부족" [checked] [ref=e142] [cursor=pointer]:
                  - generic [aria-hidden] [ref=e143]: ✓
                  - text: 정보 부족
            - radiogroup "개발 가능성" [ref=e144]:
              - generic [ref=e146]:
                - generic [aria-hidden] [ref=e147]: "2"
                - generic [ref=e148]: 개발 가능성
              - paragraph [ref=e149]: 지금 개발할 수 있는지 (가능·조건부 가능·현재 불가)
              - generic [ref=e150]:
                - generic [ref=e151]:
                  - radio "가능" [checked] [ref=e152] [cursor=pointer]:
                    - generic [aria-hidden] [ref=e153]: ✓
                    - text: 가능
                  - radio "조건부 가능" [ref=e154] [cursor=pointer]
                  - radio "현재 불가" [ref=e155] [cursor=pointer]
                - radio "정보 부족" [ref=e158] [cursor=pointer]
            - radiogroup "긴급도" [ref=e159]:
              - generic [ref=e161]:
                - generic [aria-hidden] [ref=e162]: "3"
                - generic [ref=e163]: 긴급도
              - paragraph [ref=e164]: 긴급 대응이 필요한지 (긴급·일반)
              - generic [ref=e165]:
                - generic [ref=e166]:
                  - radio "긴급" [checked] [ref=e167] [cursor=pointer]:
                    - generic [aria-hidden] [ref=e168]: ✓
                    - text: 긴급
                  - radio "일반" [ref=e169] [cursor=pointer]
                - radio "판단 보류" [ref=e172] [cursor=pointer]
            - group "참여 팀 구성" [ref=e173]:
              - generic [ref=e175]:
                - generic [aria-hidden] [ref=e176]: "4"
                - generic [ref=e177]: 참여 팀 구성
                - generic [ref=e178]: 여러 개 선택 · 없으면 비워 둡니다
              - paragraph [ref=e179]: 일을 함께 맡아야 할 팀의 조합
              - generic [ref=e181]:
                - button "AI팀" [ref=e182] [cursor=pointer]
                - button "IT팀" [ref=e183] [cursor=pointer]
                - button "현업" [pressed] [ref=e184] [cursor=pointer]:
                  - generic [aria-hidden] [ref=e185]: ✓
                  - text: 현업
            - group "위험 영역" [ref=e186]:
              - generic [ref=e188]:
                - generic [ref=e189]: 위험 영역
                - generic [ref=e190]: 여러 개 선택 · 없으면 비워 둡니다
              - paragraph [ref=e191]: 검토가 필요한 위험 분야 (임상·안전·규제 등)
              - generic [ref=e193]:
                - button "임상·안전성 검토" [ref=e194] [cursor=pointer]
                - button "약물감시 검토" [ref=e195] [cursor=pointer]
                - button "규제 검토" [ref=e196] [cursor=pointer]
            - generic [ref=e197]:
              - generic [ref=e198]:
                - generic [ref=e199]: 확신도
                - generic [aria-hidden] [ref=e200]: 80%
              - slider "확신도" [ref=e201]: "0.8"
              - generic [aria-hidden] [ref=e202]:
                - generic [ref=e203]: "0"
                - generic [ref=e204]: "25"
                - generic [ref=e205]: "50"
                - generic [ref=e206]: "75"
                - generic [ref=e207]: "100"
            - generic [ref=e208]:
              - generic [ref=e209]: 보류 사유
              - paragraph [ref=e211]: 판단을 보류할 때만 필수입니다. 확정할 때는 비워 둡니다.
              - textbox "보류 사유" [ref=e212]: 검토 표본 보류
            - group "저장 동작" [ref=e213]:
              - paragraph [ref=e214]
              - generic [ref=e215]:
                - button "확정 (Enter)" [ref=e216] [cursor=pointer]:
                  - text: 확정
                  - generic [ref=e217]: Enter
                - button "보류" [ref=e218] [cursor=pointer]
                - button "이전 (K)" [ref=e219] [cursor=pointer]:
                  - text: 이전
                  - generic [ref=e220]: K
                - button "다음 (J)" [ref=e221] [cursor=pointer]:
                  - text: 다음
                  - generic [ref=e222]: J
        - status [ref=e223]:
          - generic [ref=e224]: 보류 사유를 기록했습니다.
          - button "알림 닫기" [ref=e225] [cursor=pointer]: ×
```

# Test source

```ts
  1  | import { expect, request, test } from '@playwright/test';
  2  | 
  3  | const tenant = process.env.E2E_TENANT || 't-alpha';
  4  | const password = process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me';
  5  | 
  6  | async function login(api: import('@playwright/test').APIRequestContext, role: string) {
  7  |   const response = await api.post('/api/auth/login', { data: { email: `${role}@${tenant}.dev`, password } });
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
  38 |   await expect(page.getByText('불일치 · 합의 필요')).toBeVisible();
  39 |   await expect(page.getByRole('button', { name: '합의 라벨 확정' })).toBeVisible();
  40 |   await page.keyboard.press('j');
  41 |   await expect(sample(candidates[1].id).first()).toBeVisible();
  42 |   await page.keyboard.press('2');
  43 |   const feasibility = page.getByRole('radiogroup', { name: '개발 가능성' });
  44 |   await expect(feasibility.getByRole('radio', { checked: true })).toBeFocused();
  45 |   await page.keyboard.press('ArrowRight');
  46 |   await expect(feasibility.getByRole('radio', { checked: true })).toBeFocused();
  47 |   await page.keyboard.press('Enter');
  48 |   await expect(toast).toContainText('라벨을 확정했습니다.');
  49 |   await page.keyboard.press('j');
  50 |   await expect(sample(candidates[2].id).first()).toBeVisible();
  51 |   await page.keyboard.press('Enter');
  52 |   await expect(toast).toContainText('라벨을 확정했습니다.');
  53 |   // 4) defer needs a reason.
  54 |   await page.keyboard.press('j');
  55 |   await expect(sample(candidates[3].id).first()).toBeVisible();
  56 |   await page.getByLabel('보류 사유').fill(''); // a rerun starts from the reason saved last time
  57 |   await page.getByRole('button', { name: '보류', exact: true }).click();
  58 |   await expect(page.getByRole('alert')).toContainText('보류 사유를 입력');
  59 |   await page.getByLabel('보류 사유').fill('검토 표본 보류');
  60 |   await page.getByRole('button', { name: '보류', exact: true }).click();
  61 |   await expect(toast).toContainText('보류 사유를 기록했습니다.');
  62 |   const progress = await page.request.get('/api/evaluation/candidates?split=tuning');
  63 |   const item = (await progress.json()).progress;
> 64 |   expect(item.confirmed).toBeGreaterThanOrEqual(3);
     |                          ^ Error: expect(received).toBeGreaterThanOrEqual(expected)
  65 |   expect(item.deferred).toBeGreaterThanOrEqual(1);
  66 |   // Saved values keep the API format: strings for choices, arrays for teams and risks.
  67 |   const saved = (await (await page.request.get('/api/evaluation/candidates?split=tuning')).json()).candidates[1].my_labels.labels;
  68 |   expect(typeof saved.ai_need).toBe('string'); expect(Array.isArray(saved.team_set)).toBe(true); expect(Array.isArray(saved.risk_areas)).toBe(true);
  69 | });
  70 | 
  71 | test('final split hides predictions; the screen has no JSON text inputs and does not overflow at 375px', async ({ page }) => {
  72 |   await login(page.request, 'labeler');
  73 |   await page.setViewportSize({ width: 375, height: 800 });
  74 |   await page.goto('/evaluation');
  75 |   await expect(page.getByRole('button', { name: '확정 (Enter)' })).toBeVisible();
  76 |   await expect(page.locator('input[type="text"]')).toHaveCount(0);
  77 |   for (const tab of ['튜닝', '최종']) {
  78 |     await page.getByRole('tab', { name: tab }).click();
  79 |     await expect(page.getByRole('tab', { name: tab })).toHaveAttribute('aria-selected', 'true');
  80 |     await expect(page.getByRole('button', { name: '확정 (Enter)' })).toBeVisible();
  81 |     expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
  82 |   }
  83 |   await expect(page.getByText('모델 예측 숨김')).toBeVisible();
  84 |   await expect(page.getByText('제안 라벨')).toHaveCount(0);
  85 |   await expect(page.getByRole('button', { name: '확정 (Enter)' })).toBeDisabled();
  86 | });
  87 | 
```