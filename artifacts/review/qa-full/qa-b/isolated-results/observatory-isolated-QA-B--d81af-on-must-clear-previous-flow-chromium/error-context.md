# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: observatory-isolated.spec.ts >> QA-B-03 empty request selection must clear previous flow
- Location: ../artifacts/review/qa-full/qa-b/repro/observatory-isolated.spec.ts:17:5

# Error details

```
Error: expect(locator).toHaveCount(expected) failed

Locator:  locator('.obs-node')
Expected: 0
Received: 1
Timeout:  15000ms

Call log:
  - Expect "toHaveCount" locator('.obs-node') with timeout 15000ms
  - waiting for locator('.obs-node')
    33 × locator resolved to 1 element
       - unexpected value "1"

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
      - strong [ref=e17]: qa-b-operator
      - generic [ref=e18]: 운영자
      - button "로그아웃" [ref=e19] [cursor=pointer]
  - generic [ref=e20]:
    - banner [ref=e21]:
      - generic [ref=e22]: 의사결정 지원
      - generic [ref=e23]:
        - generic [ref=e24]: qa-b-operator · 운영자
        - generic [ref=e25]: mock
        - button "로그아웃" [ref=e26] [cursor=pointer]
    - main [ref=e27]:
      - generic [ref=e28]:
        - generic [ref=e29]:
          - generic [ref=e30]:
            - paragraph [ref=e31]: 실행 기록
            - heading "실행 관찰" [level=1] [ref=e32]
            - paragraph [ref=e33]: 실제 저장된 실행 단계와 업무·서비스 관계를 조회합니다.
          - generic [ref=e34]:
            - generic [ref=e35]:
              - generic [ref=e36]: 요청 선택
              - combobox "요청 선택" [active] [ref=e38]: req_B · 알 수 없는 상태 · 취소됨
            - generic [ref=e39]:
              - generic [ref=e40]: 실행 선택
              - combobox "실행 선택" [disabled] [ref=e42]
        - navigation "관찰 화면" [ref=e43]:
          - button "실행 Flow" [pressed] [ref=e44] [cursor=pointer]
          - button "업무 Topology" [ref=e45] [cursor=pointer]
          - button "서비스 Topology" [ref=e46] [cursor=pointer]
        - paragraph [ref=e47]:
          - text: 한 실행 안에서 단계 순서, 분기와 재시도를 봅니다. ·
          - strong [ref=e48]: 과거 재생
        - generic [ref=e49]:
          - button "처음부터" [ref=e50] [cursor=pointer]
          - button "재생" [ref=e51] [cursor=pointer]
          - generic [ref=e52]:
            - generic [ref=e53]: 속도
            - combobox "재생 속도" [ref=e55] [cursor=pointer]:
              - option "0.5×"
              - option "1×" [selected]
              - option "2×"
              - option "4×"
          - slider "재생 구간" [ref=e56]: "0"
          - button "전체 결과" [ref=e57] [cursor=pointer]
          - button "−" [ref=e58] [cursor=pointer]
          - button "전체 보기" [ref=e59] [cursor=pointer]
          - button "＋" [ref=e60] [cursor=pointer]
        - list "실행 순서" [ref=e61]:
          - listitem [ref=e62]:
            - button "1. 코드 A 요청 입력 정리 ○ 성공" [ref=e63] [cursor=pointer]:
              - generic [ref=e64]: 1. 코드
              - strong [ref=e65]: A 요청 입력 정리
              - generic [ref=e66]: ○ 성공
        - generic [ref=e67]:
          - link "같은 실행의 판단 맵 보기" [ref=e68] [cursor=pointer]:
            - /url: /judgment-map?run_id=
          - link "규칙 학습에서 보기" [ref=e69] [cursor=pointer]:
            - /url: /learning?run_id=
        - generic [ref=e70]:
          - text: 재생은 저장 기록만 읽습니다.
          - button "새 실행으로 다시 처리" [ref=e71] [cursor=pointer]
        - status [ref=e72]: "최종 실행 상태: 성공"
```

# Test source

```ts
  1  | import {test,expect} from '../../../../../frontend/node_modules/@playwright/test/index.mjs';
  2  | import {resolve} from 'node:path';
  3  | // Explicit HTTP fixture isolates the UI from shared DB outage. Shapes reuse Observatory.test.tsx.
  4  | async function fixture(page:any){
  5  |  await page.route(/http:\/\/127\.0\.0\.1:8791\/api\//,async(route:any)=>{
  6  |   const path=new URL(route.request().url()).pathname;let body:any={};
  7  |   if(path==='/api/auth/me')body={user_id:'qa-b-operator',tenant_id:'qa-b-fixture',roles:['operator'],mode:'mock'};
  8  |   else if(path==='/api/requests')body={items:[{id:'req_A',status:'completed'},{id:'req_B',status:'취소됨'}]};
  9  |   else if(path==='/api/requests/req_A/runs')body={active_run_id:'run_A',runs:[{id:'run_A',status:'succeeded'}]};
  10 |   else if(path==='/api/requests/req_B/runs')body={active_run_id:null,runs:[]};
  11 |   else if(path.endsWith('/flow'))body={request_id:'req_A',run_id:'run_A',live:false,nodes:[{id:'step_A',kind:'code',name:'A 요청 입력 정리',status:'succeeded',duration_ms:100}],edges:[]};
  12 |   else if(path.endsWith('/playback'))body={request_id:'req_A',run_id:'run_A',live:false,events:[],final_result:'succeeded',reviews:[]};
  13 |   else if(path.includes('/steps/'))body={id:'step_A',run_id:'run_A',kind:'code',name:'A 요청 입력 정리',status:'succeeded',duration_ms:100,config_version:1,versions:{schema:1},started_at:'2026-10-05T00:00:00Z',ended_at:'2026-10-05T00:00:00.100Z'};
  14 |   await route.fulfill({json:body});
  15 |  });
  16 | }
  17 | test('QA-B-03 empty request selection must clear previous flow',async({page})=>{
  18 |  await fixture(page);await page.goto('/observatory?request_id=req_A&run_id=run_A');await expect(page.locator('.obs-node')).toHaveCount(1);
  19 |  await page.getByRole('combobox',{name:'요청 선택',exact:true}).fill('req_B');await page.getByRole('option',{name:/req_B/}).click();
  20 |  await expect(page.getByRole('combobox',{name:'실행 선택',exact:true})).toBeDisabled();
  21 |  await page.screenshot({path:resolve('../artifacts/review/qa-full/qa-b/captures/stale-flow-isolated.png'),fullPage:true});
> 22 |  await expect(page.locator('.obs-node')).toHaveCount(0);
     |                                          ^ Error: expect(locator).toHaveCount(expected) failed
  23 | });
  24 | test('fixture playback has no mutation and trace has duration version',async({page})=>{
  25 |  await fixture(page);await page.goto('/observatory?request_id=req_A&run_id=run_A');await expect(page.locator('.obs-node')).toHaveCount(1);
  26 |  const mutations:string[]=[];page.on('request',r=>{if(r.url().includes('/api/')&&!['GET','HEAD'].includes(r.method()))mutations.push(r.method());});
  27 |  await page.getByRole('button',{name:'재생',exact:true}).click();await page.getByRole('button',{name:'전체 결과',exact:true}).click();await page.locator('.obs-node').click();
  28 |  await expect(page.getByRole('dialog')).toContainText('100 ms');await expect(page.getByRole('dialog')).toContainText('설정 v1');expect(mutations).toEqual([]);
  29 | });
  30 | 
```