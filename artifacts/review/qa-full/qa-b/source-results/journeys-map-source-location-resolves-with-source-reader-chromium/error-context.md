# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: journeys.spec.ts >> map source location resolves with source reader
- Location: ../artifacts/review/qa-full/qa-b/repro/journeys.spec.ts:56:5

# Error details

```
Error: expect(received).toBe(expected) // Object.is equality

Expected: 200
Received: 503
```

# Test source

```ts
  1  | import {test,expect} from '../../../../../frontend/node_modules/@playwright/test/index.mjs';
  2  | import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
  3  | import {resolve} from 'node:path';
  4  | const out=resolve('../artifacts/review/qa-full/qa-b');
  5  | const tenant=readFileSync(out+'/runtime/tenant.txt','utf8').trim();
  6  | mkdirSync(out+'/captures',{recursive:true});
> 7  | async function login(page:any,role:string){const r=await page.request.post('/api/auth/login',{data:{email:`${role}@${tenant}.dev`,password:'dev-only-change-me'}});expect(r.status()).toBe(200);}
     |                                                                                                                                                                                       ^ Error: expect(received).toBe(expected) // Object.is equality
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
  56 | test('map source location resolves with source reader',async({page})=>{
  57 |  await login(page,'source_reader');const active=await activeRun(page);await page.goto(`/judgment-map?request_id=${active.id}`);await expect(page.getByTestId('jm-board')).toBeVisible();
  58 |  await page.getByRole('button',{name:'목록 보기',exact:true}).click();await page.locator('.jm-item[data-kind="EvidenceSpan"]').first().click();await page.getByRole('button',{name:'원문 열기',exact:true}).click();
  59 |  await expect(page.getByTestId('ev-scroll')).toBeVisible();await expect(page.getByTestId('ev-scroll')).toContainText('이상반응');await page.screenshot({path:out+'/captures/map-source-resolved.png',fullPage:true});
  60 | });
  61 | 
```