# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: defects.spec.ts >> AUDIT-P1-01 a reviewer can repair an undetermined draft before approval
- Location: artifacts/review/completeness/scratch/diagnostic/defects.spec.ts:4:5

# Error details

```
Error: {"detail":{"message":"담당 조직이 tenant 범위에 없습니다"}}

expect(received).toBe(expected) // Object.is equality

Expected: 200
Received: 422
```

# Page snapshot

```yaml
- generic [ref=e3]:
  - complementary [ref=e4]:
    - generic [ref=e5]: Jev Triage
    - navigation "주 메뉴" [ref=e6]:
      - link "요청 접수" [ref=e7]:
        - /url: /
      - link "검토 대기" [ref=e8]:
        - /url: /review
      - link "업무" [ref=e9]:
        - /url: /tasks
      - link "실행 관찰" [ref=e10]:
        - /url: /observatory
      - link "판단 맵" [ref=e11]:
        - /url: /judgment-map
      - link "규칙 학습" [ref=e12]:
        - /url: /learning
      - link "모니터링" [ref=e13]:
        - /url: /monitoring
      - link "정책" [ref=e14]:
        - /url: /policy
      - link "평가 라벨" [ref=e15]:
        - /url: /evaluation
    - generic [ref=e16]:
      - strong [ref=e17]: usr_t-audit-e2e-1005_reviewer
      - generic [ref=e18]: 검토자
      - button "로그아웃" [ref=e19] [cursor=pointer]
  - generic [ref=e20]:
    - banner [ref=e21]:
      - generic [ref=e22]: 의사결정 지원
      - generic [ref=e23]:
        - generic [ref=e24]: usr_t-audit-e2e-1005_reviewer · 검토자
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
        - status [ref=e35]: 담당 조직이 tenant 범위에 없습니다
        - generic [ref=e36]:
          - navigation "검토 대기 목록" [ref=e37]:
            - heading "대기 1건" [level=2] [ref=e38]
            - generic [ref=e39]:
              - generic [ref=e40]: 상태
              - combobox "검토 상태 필터" [ref=e42]:
                - option "대기" [selected]
                - option "승인"
                - option "반려"
                - option "정보 요청"
            - generic [ref=e43] [cursor=pointer]:
              - checkbox "긴급 우선 정렬" [ref=e44]
              - generic [ref=e46]: 긴급 우선 정렬
            - 'button "분기별 시설 점검 일정을 검색하고 담당자별로 확인하고 싶습니다. 일반 req_33a60302a76c4b96906b01cdf11aab4e 대기 근거 미완료 · 개발 가능성 미충족 · 분류 미확정: 개발 가능성 · 선택 확신도 미충족: 긴급도 · 선택 확신도 미충족: 담당 조직 · 주관 · 참여 여부 불확실: IT팀 참여 확률 · 참여 여부 불확실: 현업 참여 확률 · 업무 책임 또는 산출물 누락 · 정책에서 자동 배정 비허용 검토 조직 IT팀 · 15분 대기" [ref=e47] [cursor=pointer]':
              - strong [ref=e48]: 분기별 시설 점검 일정을 검색하고 담당자별로 확인하고 싶습니다.
              - generic [ref=e49]:
                - generic [ref=e50]: 일반
                - code [ref=e51]:
                  - text: req_…1aab4e
                  - generic [ref=e52]: req_33a60302a76c4b96906b01cdf11aab4e
              - generic [ref=e53]:
                - generic [aria-hidden] [ref=e54]: ○
                - text: 대기
              - generic [ref=e55]: "근거 미완료 · 개발 가능성 미충족 · 분류 미확정: 개발 가능성 · 선택 확신도 미충족: 긴급도 · 선택 확신도 미충족: 담당 조직 · 주관 · 참여 여부 불확실: IT팀 참여 확률 · 참여 여부 불확실: 현업 참여 확률 · 업무 책임 또는 산출물 누락 · 정책에서 자동 배정 비허용"
              - generic [ref=e56]: 검토 조직 IT팀 · 15분 대기
          - article [ref=e57]:
            - heading "분기별 시설 점검 일정을 검색하고 담당자별로 확인하고 싶습니다." [level=2] [ref=e58]
            - paragraph [ref=e59]:
              - text: 요청
              - code [ref=e60]:
                - text: req_…1aab4e
                - generic [ref=e61]: req_33a60302a76c4b96906b01cdf11aab4e
              - text: · revision
              - code [ref=e62]:
                - text: rev_…2607ae
                - generic [ref=e63]: rev_e6917c416c8c41cc943412a8e92607ae
              - text: · run
              - code [ref=e64]:
                - text: run_…3d8544
                - generic [ref=e65]: run_4c5a5a8e145b4a1b9e294720783d8544
            - generic [ref=e66]:
              - heading "요청 내용" [level=3] [ref=e67]
              - note [ref=e68]:
                - paragraph [ref=e69]: 원문 열람 권한이 없습니다. 제목과 허용된 마스킹 요약만 표시합니다.
            - generic [ref=e70]:
              - heading "AI 원안과 검토 값" [level=3] [ref=e71]
              - generic [ref=e72]:
                - text: AI 필요성
                - generic [ref=e73]:
                  - generic [ref=e74]: "원안: 불필요"
                  - textbox "AI 필요성 수정" [ref=e75]: 불필요
              - generic [ref=e76]:
                - text: 개발 가능성
                - generic [ref=e77]:
                  - generic [ref=e78]: "원안: 정보 부족"
                  - textbox "개발 가능성 수정" [ref=e79]: 가능
              - generic [ref=e80]:
                - text: 긴급도
                - generic [ref=e81]:
                  - generic [ref=e82]: "원안: 일반"
                  - textbox "긴급도 수정" [ref=e83]: 일반
              - generic [ref=e84]:
                - text: 담당 조직
                - generic [ref=e85]:
                  - generic [ref=e86]: "원안: IT팀"
                  - textbox "담당 조직 수정" [ref=e87]: IT팀
            - generic [ref=e88]:
              - heading "신뢰 신호와 원문 근거" [level=3] [ref=e89]
              - generic [ref=e90]:
                - strong [ref=e91]: AI 필요성 · 선택형
                - text: 불필요 (확신도 99%)
              - generic [ref=e92]:
                - strong [ref=e93]: 개발 가능성 · 선택형
                - text: 정보 부족 (확신도 88%)
              - generic [ref=e94]:
                - strong [ref=e95]: 긴급도 · 선택형
                - text: 일반 (확신도 26%)
              - generic [ref=e96]:
                - strong [ref=e97]: 담당 조직 · 주관 · 선택형
                - text: IT팀 (확신도 51%)
              - generic [ref=e98]:
                - strong [ref=e99]: AI팀 참여 확률 · 확률형
                - text: 확률 16%
              - generic [ref=e100]:
                - strong [ref=e101]: IT팀 참여 확률 · 확률형
                - text: 확률 65%
              - generic [ref=e102]:
                - strong [ref=e103]: 현업 참여 확률 · 확률형
                - text: 확률 40%
              - generic [ref=e104]:
                - strong [ref=e105]: 임상·안전 위험 확률 · 확률형
                - text: 확률 9%
              - generic [ref=e106]:
                - strong [ref=e107]: 약물 감시 위험 확률 · 확률형
                - text: 확률 6%
              - generic [ref=e108]:
                - strong [ref=e109]: 규제 대응 위험 확률 · 확률형
                - text: 확률 12%
              - generic [ref=e110]:
                - strong [ref=e111]: 검토 필요도 · 점수형
                - text: 50%
            - generic [ref=e112]:
              - heading "업무 분담 원안" [level=3] [ref=e113]
              - generic [ref=e114]:
                - paragraph [ref=e115]: 업무 분해 미정 · 미정 · 선행 없음 · 산출물 필요 업무 유형 확인
                - generic [ref=e116]:
                  - text: 주관 조직
                  - textbox "주관 조직" [ref=e117]: IT팀
                - generic [ref=e118]:
                  - text: 협업 조직
                  - textbox "협업 조직" [ref=e119]
                - generic [ref=e120]: "AI 원안: 미정 / 협업 없음"
            - generic [ref=e121]:
              - text: 결정 사유
              - textbox "결정 사유" [ref=e122]: "감사 재현: 업무 담당 조직을 올바르게 수정한 뒤 승인합니다."
            - paragraph [ref=e123]:
              - text: 이 수정은 이 요청에만 적용됩니다. 공통 규칙은 규칙 학습에서 별도로 검토합니다.
              - link "규칙 학습 열기" [ref=e124]:
                - /url: /learning
            - region "규칙 학습 연결" [ref=e125]:
              - heading "규칙 학습 연결" [level=3] [ref=e126]
              - paragraph [ref=e127]: 이 요청의 수정 승인은 이 요청에만 적용됩니다. 요청 한 건의 수정 승인은 규칙 게시가 아닙니다. 공통 규칙은 규칙 학습에서 규칙 관리자가 별도로 검토합니다.
              - paragraph [ref=e128]: 저장된 수정 기록이 없습니다. 원안 그대로 승인된 요청은 비교할 수정이 없습니다.
              - paragraph [ref=e129]:
                - link "규칙 학습 열기" [ref=e130]:
                  - /url: /learning
                - text: ·
                - link "판단 맵에서 경로 보기" [ref=e131]:
                  - /url: /judgment-map?request_id=req_33a60302a76c4b96906b01cdf11aab4e
            - heading "결정 이력" [level=3] [ref=e133]
            - generic [ref=e134]:
              - button "승인" [ref=e135] [cursor=pointer]
              - button "수정 승인" [ref=e136] [cursor=pointer]
              - button "반려" [ref=e137] [cursor=pointer]
              - button "정보 요청" [ref=e138] [cursor=pointer]
```

# Test source

```ts
  1  | import {test,expect} from '@playwright/test';
  2  | const tenant='t-audit-e2e-1005';
  3  | async function login(page:any,role:string){const r=await page.request.post('/api/auth/login',{data:{email:`${role}@${tenant}.dev`,password:'dev-only-change-me'}});expect(r.status()).toBe(200);}
  4  | test('AUDIT-P1-01 a reviewer can repair an undetermined draft before approval',async({page})=>{
  5  |  await login(page,'reviewer');await page.goto('/review?request_id=req_33a60302a76c4b96906b01cdf11aab4e');
  6  |  await page.getByLabel('개발 가능성 수정').fill('가능');await page.getByLabel('주관 조직',{exact:true}).fill('IT팀');await page.getByLabel('결정 사유',{exact:true}).fill('감사 재현: 업무 담당 조직을 올바르게 수정한 뒤 승인합니다.');
> 7  |  const response=page.waitForResponse(r=>r.url().includes('/decision')&&r.request().method()==='POST');await page.getByRole('button',{name:'수정 승인',exact:true}).click();const r=await response;expect(r.status(),await r.text()).toBe(200);
     |                                                                                                                                                                                                                                 ^ Error: {"detail":{"message":"담당 조직이 tenant 범위에 없습니다"}}
  8  | });
  9  | test('AUDIT-P1-02 completed confirmation enables the main task start button',async({page})=>{
  10 |  await login(page,'team_member');await page.goto('/tasks');await page.locator('.task-list button',{hasText:'감사 시드: 확인 완료 후 시작'}).click();
  11 |  const dialog=page.getByRole('dialog',{name:'업무 상세'});await expect(dialog).toContainText('감사 시드: 완료된 사전 확인 · 완료');await expect(dialog.getByRole('button',{name:'진행으로 변경'})).toBeEnabled();
  12 | });
  13 | 
```