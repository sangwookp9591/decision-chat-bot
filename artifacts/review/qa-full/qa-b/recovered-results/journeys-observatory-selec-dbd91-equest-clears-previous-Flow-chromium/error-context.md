# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: journeys.spec.ts >> observatory selecting an empty request clears previous Flow
- Location: ../artifacts/review/qa-full/qa-b/repro/journeys.spec.ts:27:5

# Error details

```
Error: expect(locator).toHaveCount(expected) failed

Locator:  locator('.obs-node')
Expected: 0
Received: 8
Timeout:  15000ms

Call log:
  - Expect "toHaveCount" locator('.obs-node') with timeout 15000ms
  - waiting for locator('.obs-node')
    34 × locator resolved to 8 elements
       - unexpected value "8"

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
      - strong [ref=e17]: usr_t-qa-b-1005181417_operator
      - generic [ref=e18]: 운영자
      - button "로그아웃" [ref=e19] [cursor=pointer]
  - generic [ref=e20]:
    - banner [ref=e21]:
      - generic [ref=e22]: 의사결정 지원
      - generic [ref=e23]:
        - generic [ref=e24]: usr_t-qa-b-1005181417_operator · 운영자
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
              - combobox "요청 선택" [active] [ref=e38]: t-qa-b-1005181417-layout-1 · 알 수 없는 상태 · 취소됨
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
            - button "1. 코드 입력 정리 ○ 성공 재시도 att_9ecf80543bfd4b1e96382369a6097c23" [ref=e63] [cursor=pointer]:
              - generic [ref=e64]: 1. 코드
              - strong [ref=e65]: 입력 정리
              - generic [ref=e66]: ○ 성공
              - generic [ref=e67]: 재시도 att_9ecf80543bfd4b1e96382369a6097c23
          - listitem [ref=e68]:
            - generic [aria-hidden] [ref=e69]: →
            - button "2. AI Jev 판단 ○ 성공 재시도 att_9ecf80543bfd4b1e96382369a6097c23 선행 입력 정리" [ref=e70] [cursor=pointer]:
              - generic [ref=e71]: 2. AI
              - strong [ref=e72]: Jev 판단
              - generic [ref=e73]: ○ 성공
              - generic [ref=e74]: 재시도 att_9ecf80543bfd4b1e96382369a6097c23
              - generic [ref=e75]: 선행 입력 정리
          - listitem [ref=e76]:
            - generic [aria-hidden] [ref=e77]: →
            - button "3. AI 업무 분해 ○ 성공 재시도 att_9ecf80543bfd4b1e96382369a6097c23 선행 Jev 판단" [ref=e78] [cursor=pointer]:
              - generic [ref=e79]: 3. AI
              - strong [ref=e80]: 업무 분해
              - generic [ref=e81]: ○ 성공
              - generic [ref=e82]: 재시도 att_9ecf80543bfd4b1e96382369a6097c23
              - generic [ref=e83]: 선행 Jev 판단
          - listitem [ref=e84]:
            - generic [aria-hidden] [ref=e85]: →
            - button "4. AI 근거 연결 ○ 성공 재시도 att_9ecf80543bfd4b1e96382369a6097c23 선행 업무 분해" [ref=e86] [cursor=pointer]:
              - generic [ref=e87]: 4. AI
              - strong [ref=e88]: 근거 연결
              - generic [ref=e89]: ○ 성공
              - generic [ref=e90]: 재시도 att_9ecf80543bfd4b1e96382369a6097c23
              - generic [ref=e91]: 선행 업무 분해
          - listitem [ref=e92]:
            - generic [aria-hidden] [ref=e93]: →
            - button "5. 규칙 규칙 적용 ○ 성공 재시도 att_9ecf80543bfd4b1e96382369a6097c23 선행 근거 연결" [ref=e94] [cursor=pointer]:
              - generic [ref=e95]: 5. 규칙
              - strong [ref=e96]: 규칙 적용
              - generic [ref=e97]: ○ 성공
              - generic [ref=e98]: 재시도 att_9ecf80543bfd4b1e96382369a6097c23
              - generic [ref=e99]: 선행 근거 연결
          - listitem [ref=e100]:
            - generic [aria-hidden] [ref=e101]: →
            - button "6. 규칙 자동 배정 조건 검사 ○ 성공 재시도 att_9ecf80543bfd4b1e96382369a6097c23 선행 규칙 적용" [ref=e102] [cursor=pointer]:
              - generic [ref=e103]: 6. 규칙
              - strong [ref=e104]: 자동 배정 조건 검사
              - generic [ref=e105]: ○ 성공
              - generic [ref=e106]: 재시도 att_9ecf80543bfd4b1e96382369a6097c23
              - generic [ref=e107]: 선행 규칙 적용
          - listitem [ref=e108]:
            - generic [aria-hidden] [ref=e109]: →
            - button "7. 코드 결과 저장 ○ 성공 재시도 att_9ecf80543bfd4b1e96382369a6097c23 선행 자동 배정 조건 검사" [ref=e110] [cursor=pointer]:
              - generic [ref=e111]: 7. 코드
              - strong [ref=e112]: 결과 저장
              - generic [ref=e113]: ○ 성공
              - generic [ref=e114]: 재시도 att_9ecf80543bfd4b1e96382369a6097c23
              - generic [ref=e115]: 선행 자동 배정 조건 검사
          - listitem [ref=e116]:
            - generic [aria-hidden] [ref=e117]: →
            - button "8. 사람 사람 검토 ○ 사람 검토 대기 선행 결과 저장" [ref=e118] [cursor=pointer]:
              - generic [ref=e119]: 8. 사람
              - strong [ref=e120]: 사람 검토
              - generic [ref=e121]: ○ 사람 검토 대기
              - generic [ref=e122]: 선행 결과 저장
          - listitem [ref=e123]: 사람 대기 압축 · 실제 0초
        - list "실행 관계" [ref=e124]:
          - listitem [ref=e125]: 입력 정리 → Jev 판단
          - listitem [ref=e126]: Jev 판단 → 업무 분해
          - listitem [ref=e127]: 업무 분해 → 근거 연결
          - listitem [ref=e128]: 근거 연결 → 규칙 적용
          - listitem [ref=e129]: 규칙 적용 → 자동 배정 조건 검사
          - listitem [ref=e130]: 자동 배정 조건 검사 → 결과 저장
          - listitem [ref=e131]: 결과 저장 → 사람 검토
        - generic [ref=e132]:
          - link "같은 실행의 판단 맵 보기" [ref=e133] [cursor=pointer]:
            - /url: /judgment-map?run_id=
          - link "규칙 학습에서 보기" [ref=e134] [cursor=pointer]:
            - /url: /learning?run_id=
        - generic [ref=e135]:
          - text: 재생은 저장 기록만 읽습니다.
          - button "새 실행으로 다시 처리" [ref=e136] [cursor=pointer]
        - status [ref=e137]: "최종 실행 상태: 판단 저장 완료"
```

# Test source

```ts
  1  | import {test,expect} from '../../../../../frontend/node_modules/@playwright/test/index.mjs';
  2  | import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
  3  | import {resolve} from 'node:path';
  4  | const out=resolve('../artifacts/review/qa-full/qa-b');
  5  | const tenant=readFileSync(out+'/runtime/tenant.txt','utf8').trim();
  6  | mkdirSync(out+'/captures',{recursive:true});
  7  | async function login(page:any,role:string){const r=await page.request.post('/api/auth/login',{data:{email:`${role}@${tenant}.dev`,password:'dev-only-change-me'}});expect(r.status()).toBe(200);}
  8  | const routes=['/','/review','/tasks','/observatory','/judgment-map','/learning','/monitoring','/policy','/evaluation'];
  9  | for(const role of ['requester','reviewer','team_member','operator','policy_editor','rule_admin','labeler']){
  10 |  test(`screens ${role}`,async({page})=>{
  11 |   test.setTimeout(240000);await login(page,role);const rows:any[]=[];const errors:string[]=[];
  12 |   page.on('pageerror',e=>errors.push(e.message));
  13 |   for(const path of routes){await page.goto(path);await expect(page.locator('main h1')).toBeVisible();await page.waitForTimeout(500);
  14 |    rows.push({path,text:await page.locator('main').innerText(),overflow:await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)});
  15 |   }
  16 |   writeFileSync(out+`/screens-${role}.json`,JSON.stringify({role,rows,errors},null,2));expect(errors).toEqual([]);
  17 |  });
  18 | }
  19 | for(const [path,role] of [['/observatory','operator'],['/judgment-map','reviewer'],['/learning','rule_admin'],['/monitoring','operator'],['/policy','policy_editor'],['/evaluation','labeler']]){
  20 |  test(`mobile dark ${path}`,async({page})=>{
  21 |   await login(page,role);await page.setViewportSize({width:375,height:812});await page.emulateMedia({colorScheme:'dark'});await page.goto(path);await expect(page.locator('main h1')).toBeVisible();
  22 |   await page.waitForTimeout(1500);await page.keyboard.press('Tab');await page.screenshot({path:out+`/captures/mobile-${path.slice(1)}.png`,fullPage:true});
  23 |   expect(await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
  24 |  });
  25 | }
  26 | async function activeRun(page:any){const items=(await(await page.request.get('/api/requests')).json()).items;for(const item of items){const r=await(await page.request.get(`/api/requests/${item.id}/runs`)).json();if(r.runs?.length)return {id:item.id,run:r.runs[0].id,items};}throw Error('fixture must have a real run');}
  27 | test('observatory selecting an empty request clears previous Flow',async({page})=>{
  28 |  await login(page,'operator');const active=await activeRun(page);
  29 |  await page.goto(`/observatory?request_id=${active.id}&run_id=${active.run}`);await expect(page.locator('.obs-node').first()).toBeVisible();
  30 |  const empty=active.items.find((x:any)=>x.id.includes('-layout-'));
  31 |  await page.getByRole('combobox',{name:'요청 선택',exact:true}).fill(empty.id);
  32 |  await page.getByRole('option',{name:new RegExp('^'+empty.id+' ·')}).click();
  33 |  await expect(page.getByRole('combobox',{name:'실행 선택',exact:true})).toBeDisabled();
  34 |  await page.screenshot({path:out+'/captures/stale-flow.png',fullPage:true});
> 35 |  await expect(page.locator('.obs-node')).toHaveCount(0);
     |                                          ^ Error: expect(locator).toHaveCount(expected) failed
  36 | });
  37 | test('playback is read only and trace opens',async({page})=>{
  38 |  await login(page,'operator');const active=await activeRun(page);await page.goto(`/observatory?run_id=${active.run}`);await expect(page.locator('.obs-node').first()).toBeVisible();
  39 |  const mutations:string[]=[];page.on('request',r=>{if(r.url().includes('/api/')&&!['GET','HEAD'].includes(r.method()))mutations.push(r.method()+' '+r.url());});
  40 |  await page.getByRole('button',{name:'재생',exact:true}).click();await page.getByRole('button',{name:'전체 결과',exact:true}).click();
  41 |  await page.locator('.obs-node').first().click();const drawer=page.getByRole('dialog',{name:'Trace 상세'});await expect(drawer).toContainText('오류 분류');await expect(drawer).toContainText('실행 버전');
  42 |  await page.screenshot({path:out+'/captures/trace.png',fullPage:true});expect(mutations).toEqual([]);
  43 | });
  44 | test('real judgment map navigation and details',async({page,context})=>{
  45 |  await login(page,'reviewer');const active=await activeRun(page);const graph=await(await page.request.get(`/api/graph/judgment?request_id=${active.id}`)).json();
  46 |  expect(graph.nodes.length).toBeGreaterThan(0);await page.goto(`/judgment-map?request_id=${active.id}`);await expect(page.getByTestId('jm-board')).toHaveAttribute('data-node-count',String(graph.node_count));
  47 |  const before=await page.getByTestId('jm-zoom-pct').innerText();await page.getByRole('button',{name:'확대',exact:true}).click();await expect(page.getByTestId('jm-zoom-pct')).not.toHaveText(before);
  48 |  await page.getByRole('button',{name:'축소',exact:true}).click();await page.getByRole('button',{name:'전체 보기',exact:true}).click();
  49 |  await page.getByRole('button',{name:'크게 보기',exact:true}).click();await expect(page.locator('.jm-page')).toHaveClass(/is-expanded/);await page.keyboard.press('Escape');await expect(page.locator('.jm-page')).not.toHaveClass(/is-expanded/);
  50 |  await page.getByRole('button',{name:'목록 보기',exact:true}).click();await expect(page.locator('.jm-item')).toHaveCount(graph.node_count);
  51 |  await page.locator('.jm-item').first().focus();await page.keyboard.press('ArrowRight');await page.keyboard.press('Enter');await expect(page.getByTestId('jm-detail')).toBeVisible();
  52 |  await context.grantPermissions(['clipboard-read','clipboard-write']);await page.getByRole('button',{name:'ID 복사'}).click();await expect(page.getByRole('button',{name:'ID 복사'})).toHaveText('복사됨');
  53 |  await page.screenshot({path:out+'/captures/map-detail.png',fullPage:true});
  54 |  const evidence=page.locator('.jm-item[data-kind="EvidenceSpan"]').first();if(await evidence.count()){await evidence.click();await page.getByRole('button',{name:'원문 열기',exact:true}).click();await expect(page.getByRole('dialog')).toBeVisible();await page.screenshot({path:out+'/captures/map-source.png',fullPage:true});}
  55 | });
  56 | test('map source location resolves with source reader',async({page})=>{
  57 |  await login(page,'source_reader');const active=await activeRun(page);await page.goto(`/judgment-map?request_id=${active.id}`);await expect(page.getByTestId('jm-board')).toBeVisible();
  58 |  await page.getByRole('button',{name:'목록 보기',exact:true}).click();await page.locator('.jm-item[data-kind="EvidenceSpan"]').first().click();await page.getByRole('button',{name:'원문 열기',exact:true}).click();
  59 |  await expect(page.getByTestId('ev-scroll')).toBeVisible();await expect(page.getByTestId('ev-scroll')).toContainText('이상반응');await page.screenshot({path:out+'/captures/map-source-resolved.png',fullPage:true});
  60 | });
  61 | 
```