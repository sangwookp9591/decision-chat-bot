# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: journeys.spec.ts >> observatory selecting an empty request clears previous Flow
- Location: ../artifacts/review/qa-full/qa-b/repro/journeys.spec.ts:27:5

# Error details

```
Error: locator.click: Error: strict mode violation: getByRole('option').filter({ hasText: 't-qa-b-1005181417-layout-1' }) resolved to 11 elements:
    1) <li id=":r1:-o0" role="option" class="active" aria-selected="false">t-qa-b-1005181417-layout-1 · 알 수 없는 상태 · 취소됨</li> aka getByRole('option', { name: 't-qa-b-1005181417-layout-1 · 알 수 없는 상태 · 취소됨' })
    2) <li class="" id=":r1:-o1" role="option" aria-selected="false">t-qa-b-1005181417-layout-10 · 알 수 없는 상태 · 취소됨</li> aka getByRole('option', { name: 't-qa-b-1005181417-layout-10' })
    3) <li class="" id=":r1:-o2" role="option" aria-selected="false">t-qa-b-1005181417-layout-11 · 알 수 없는 상태 · 취소됨</li> aka getByRole('option', { name: 't-qa-b-1005181417-layout-11' })
    4) <li class="" id=":r1:-o3" role="option" aria-selected="false">t-qa-b-1005181417-layout-12 · 알 수 없는 상태 · 취소됨</li> aka getByRole('option', { name: 't-qa-b-1005181417-layout-12' })
    5) <li class="" id=":r1:-o4" role="option" aria-selected="false">t-qa-b-1005181417-layout-13 · 알 수 없는 상태 · 취소됨</li> aka getByRole('option', { name: 't-qa-b-1005181417-layout-13' })
    6) <li class="" id=":r1:-o5" role="option" aria-selected="false">t-qa-b-1005181417-layout-14 · 알 수 없는 상태 · 취소됨</li> aka getByRole('option', { name: 't-qa-b-1005181417-layout-14' })
    7) <li class="" id=":r1:-o6" role="option" aria-selected="false">t-qa-b-1005181417-layout-15 · 알 수 없는 상태 · 취소됨</li> aka getByRole('option', { name: 't-qa-b-1005181417-layout-15' })
    8) <li class="" id=":r1:-o7" role="option" aria-selected="false">t-qa-b-1005181417-layout-16 · 알 수 없는 상태 · 취소됨</li> aka getByRole('option', { name: 't-qa-b-1005181417-layout-16' })
    9) <li class="" id=":r1:-o8" role="option" aria-selected="false">t-qa-b-1005181417-layout-17 · 알 수 없는 상태 · 취소됨</li> aka getByRole('option', { name: 't-qa-b-1005181417-layout-17' })
    10) <li class="" id=":r1:-o9" role="option" aria-selected="false">t-qa-b-1005181417-layout-18 · 알 수 없는 상태 · 취소됨</li> aka getByRole('option', { name: 't-qa-b-1005181417-layout-18' })
    ...

Call log:
  - waiting for getByRole('option').filter({ hasText: 't-qa-b-1005181417-layout-1' })

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
              - combobox "요청 선택" [expanded] [active] [ref=e38]: t-qa-b-1005181417-layout-1
              - listbox "요청 선택 목록" [ref=e39]:
                - option "t-qa-b-1005181417-layout-1 · 알 수 없는 상태 · 취소됨" [ref=e40] [cursor=pointer]
                - option "t-qa-b-1005181417-layout-10 · 알 수 없는 상태 · 취소됨" [ref=e41] [cursor=pointer]
                - option "t-qa-b-1005181417-layout-11 · 알 수 없는 상태 · 취소됨" [ref=e42] [cursor=pointer]
                - option "t-qa-b-1005181417-layout-12 · 알 수 없는 상태 · 취소됨" [ref=e43] [cursor=pointer]
                - option "t-qa-b-1005181417-layout-13 · 알 수 없는 상태 · 취소됨" [ref=e44] [cursor=pointer]
                - option "t-qa-b-1005181417-layout-14 · 알 수 없는 상태 · 취소됨" [ref=e45] [cursor=pointer]
                - option "t-qa-b-1005181417-layout-15 · 알 수 없는 상태 · 취소됨" [ref=e46] [cursor=pointer]
                - option "t-qa-b-1005181417-layout-16 · 알 수 없는 상태 · 취소됨" [ref=e47] [cursor=pointer]
                - option "t-qa-b-1005181417-layout-17 · 알 수 없는 상태 · 취소됨" [ref=e48] [cursor=pointer]
                - option "t-qa-b-1005181417-layout-18 · 알 수 없는 상태 · 취소됨" [ref=e49] [cursor=pointer]
                - option "t-qa-b-1005181417-layout-19 · 알 수 없는 상태 · 취소됨" [ref=e50] [cursor=pointer]
            - generic [ref=e51]:
              - generic [ref=e52]: 실행 선택
              - combobox "실행 선택" [ref=e54]: run_a6ac767b3239410bae9a46f1ef8c30d6 · 판단 저장 완료
        - navigation "관찰 화면" [ref=e55]:
          - button "실행 Flow" [pressed] [ref=e56] [cursor=pointer]
          - button "업무 Topology" [ref=e57] [cursor=pointer]
          - button "서비스 Topology" [ref=e58] [cursor=pointer]
        - paragraph [ref=e59]:
          - text: 한 실행 안에서 단계 순서, 분기와 재시도를 봅니다. ·
          - strong [ref=e60]: 과거 재생
        - generic [ref=e61]:
          - button "처음부터" [ref=e62] [cursor=pointer]
          - button "재생" [ref=e63] [cursor=pointer]
          - generic [ref=e64]:
            - generic [ref=e65]: 속도
            - combobox "재생 속도" [ref=e67] [cursor=pointer]:
              - option "0.5×"
              - option "1×" [selected]
              - option "2×"
              - option "4×"
          - slider "재생 구간" [ref=e68]: "0"
          - button "전체 결과" [ref=e69] [cursor=pointer]
          - button "−" [ref=e70] [cursor=pointer]
          - button "전체 보기" [ref=e71] [cursor=pointer]
          - button "＋" [ref=e72] [cursor=pointer]
        - list "실행 순서" [ref=e73]:
          - listitem [ref=e74]:
            - button "1. 코드 입력 정리 ○ 성공 재시도 att_9ecf80543bfd4b1e96382369a6097c23" [ref=e75] [cursor=pointer]:
              - generic [ref=e76]: 1. 코드
              - strong [ref=e77]: 입력 정리
              - generic [ref=e78]: ○ 성공
              - generic [ref=e79]: 재시도 att_9ecf80543bfd4b1e96382369a6097c23
          - listitem [ref=e80]:
            - generic [aria-hidden] [ref=e81]: →
            - button "2. AI Jev 판단 ○ 성공 재시도 att_9ecf80543bfd4b1e96382369a6097c23 선행 입력 정리" [ref=e82] [cursor=pointer]:
              - generic [ref=e83]: 2. AI
              - strong [ref=e84]: Jev 판단
              - generic [ref=e85]: ○ 성공
              - generic [ref=e86]: 재시도 att_9ecf80543bfd4b1e96382369a6097c23
              - generic [ref=e87]: 선행 입력 정리
          - listitem [ref=e88]:
            - generic [aria-hidden] [ref=e89]: →
            - button "3. AI 업무 분해 ○ 성공 재시도 att_9ecf80543bfd4b1e96382369a6097c23 선행 Jev 판단" [ref=e90] [cursor=pointer]:
              - generic [ref=e91]: 3. AI
              - strong [ref=e92]: 업무 분해
              - generic [ref=e93]: ○ 성공
              - generic [ref=e94]: 재시도 att_9ecf80543bfd4b1e96382369a6097c23
              - generic [ref=e95]: 선행 Jev 판단
          - listitem [ref=e96]:
            - generic [aria-hidden] [ref=e97]: →
            - button "4. AI 근거 연결 ○ 성공 재시도 att_9ecf80543bfd4b1e96382369a6097c23 선행 업무 분해" [ref=e98] [cursor=pointer]:
              - generic [ref=e99]: 4. AI
              - strong [ref=e100]: 근거 연결
              - generic [ref=e101]: ○ 성공
              - generic [ref=e102]: 재시도 att_9ecf80543bfd4b1e96382369a6097c23
              - generic [ref=e103]: 선행 업무 분해
          - listitem [ref=e104]:
            - generic [aria-hidden] [ref=e105]: →
            - button "5. 규칙 규칙 적용 ○ 성공 재시도 att_9ecf80543bfd4b1e96382369a6097c23 선행 근거 연결" [ref=e106] [cursor=pointer]:
              - generic [ref=e107]: 5. 규칙
              - strong [ref=e108]: 규칙 적용
              - generic [ref=e109]: ○ 성공
              - generic [ref=e110]: 재시도 att_9ecf80543bfd4b1e96382369a6097c23
              - generic [ref=e111]: 선행 근거 연결
          - listitem [ref=e112]:
            - generic [aria-hidden] [ref=e113]: →
            - button "6. 규칙 자동 배정 조건 검사 ○ 성공 재시도 att_9ecf80543bfd4b1e96382369a6097c23 선행 규칙 적용" [ref=e114] [cursor=pointer]:
              - generic [ref=e115]: 6. 규칙
              - strong [ref=e116]: 자동 배정 조건 검사
              - generic [ref=e117]: ○ 성공
              - generic [ref=e118]: 재시도 att_9ecf80543bfd4b1e96382369a6097c23
              - generic [ref=e119]: 선행 규칙 적용
          - listitem [ref=e120]:
            - generic [aria-hidden] [ref=e121]: →
            - button "7. 코드 결과 저장 ○ 성공 재시도 att_9ecf80543bfd4b1e96382369a6097c23 선행 자동 배정 조건 검사" [ref=e122] [cursor=pointer]:
              - generic [ref=e123]: 7. 코드
              - strong [ref=e124]: 결과 저장
              - generic [ref=e125]: ○ 성공
              - generic [ref=e126]: 재시도 att_9ecf80543bfd4b1e96382369a6097c23
              - generic [ref=e127]: 선행 자동 배정 조건 검사
          - listitem [ref=e128]:
            - generic [aria-hidden] [ref=e129]: →
            - button "8. 사람 사람 검토 ○ 사람 검토 대기 선행 결과 저장" [ref=e130] [cursor=pointer]:
              - generic [ref=e131]: 8. 사람
              - strong [ref=e132]: 사람 검토
              - generic [ref=e133]: ○ 사람 검토 대기
              - generic [ref=e134]: 선행 결과 저장
          - listitem [ref=e135]: 사람 대기 압축 · 실제 0초
        - list "실행 관계" [ref=e136]:
          - listitem [ref=e137]: 입력 정리 → Jev 판단
          - listitem [ref=e138]: Jev 판단 → 업무 분해
          - listitem [ref=e139]: 업무 분해 → 근거 연결
          - listitem [ref=e140]: 근거 연결 → 규칙 적용
          - listitem [ref=e141]: 규칙 적용 → 자동 배정 조건 검사
          - listitem [ref=e142]: 자동 배정 조건 검사 → 결과 저장
          - listitem [ref=e143]: 결과 저장 → 사람 검토
        - generic [ref=e144]:
          - link "같은 실행의 판단 맵 보기" [ref=e145] [cursor=pointer]:
            - /url: /judgment-map?run_id=run_a6ac767b3239410bae9a46f1ef8c30d6
          - link "규칙 학습에서 보기" [ref=e146] [cursor=pointer]:
            - /url: /learning?run_id=run_a6ac767b3239410bae9a46f1ef8c30d6
        - generic [ref=e147]:
          - text: 재생은 저장 기록만 읽습니다.
          - button "새 실행으로 다시 처리" [ref=e148] [cursor=pointer]
        - status [ref=e149]: "최종 실행 상태: 판단 저장 완료"
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
> 32 |  await page.getByRole('option').filter({hasText:empty.id}).click();
     |                                                            ^ Error: locator.click: Error: strict mode violation: getByRole('option').filter({ hasText: 't-qa-b-1005181417-layout-1' }) resolved to 11 elements:
  33 |  await expect(page.getByRole('combobox',{name:'실행 선택',exact:true})).toBeDisabled();
  34 |  await page.screenshot({path:out+'/captures/stale-flow.png',fullPage:true});
  35 |  await expect(page.locator('.obs-node')).toHaveCount(0);
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
  56 | 
```