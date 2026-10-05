import {test,expect} from '../../../../../frontend/node_modules/@playwright/test/index.mjs';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve} from 'node:path';
const out=resolve('../artifacts/review/qa-full/qa-b');
const tenant=readFileSync(out+'/runtime/tenant.txt','utf8').trim();
mkdirSync(out+'/captures',{recursive:true});
async function login(page:any,role:string){const r=await page.request.post('/api/auth/login',{data:{email:`${role}@${tenant}.dev`,password:'dev-only-change-me'}});expect(r.status()).toBe(200);}
const routes=['/','/review','/tasks','/observatory','/judgment-map','/learning','/monitoring','/policy','/evaluation'];
for(const role of ['requester','reviewer','team_member','operator','policy_editor','rule_admin','labeler']){
 test(`screens ${role}`,async({page})=>{
  test.setTimeout(240000);await login(page,role);const rows:any[]=[];const errors:string[]=[];
  page.on('pageerror',e=>errors.push(e.message));
  for(const path of routes){await page.goto(path);await expect(page.locator('main h1')).toBeVisible();await page.waitForTimeout(500);
   rows.push({path,text:await page.locator('main').innerText(),overflow:await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)});
  }
  writeFileSync(out+`/screens-${role}.json`,JSON.stringify({role,rows,errors},null,2));expect(errors).toEqual([]);
 });
}
for(const [path,role] of [['/observatory','operator'],['/judgment-map','reviewer'],['/learning','rule_admin'],['/monitoring','operator'],['/policy','policy_editor'],['/evaluation','labeler']]){
 test(`mobile dark ${path}`,async({page})=>{
  await login(page,role);await page.setViewportSize({width:375,height:812});await page.emulateMedia({colorScheme:'dark'});await page.goto(path);await expect(page.locator('main h1')).toBeVisible();
  await page.waitForTimeout(1500);await page.keyboard.press('Tab');await page.screenshot({path:out+`/captures/mobile-${path.slice(1)}.png`,fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
 });
}
async function activeRun(page:any){const items=(await(await page.request.get('/api/requests')).json()).items;for(const item of items){const r=await(await page.request.get(`/api/requests/${item.id}/runs`)).json();if(r.runs?.length)return {id:item.id,run:r.runs[0].id,items};}throw Error('fixture must have a real run');}
test('observatory selecting an empty request clears previous Flow',async({page})=>{
 await login(page,'operator');const active=await activeRun(page);
 await page.goto(`/observatory?request_id=${active.id}&run_id=${active.run}`);await expect(page.locator('.obs-node').first()).toBeVisible();
 const empty=active.items.find((x:any)=>x.id.includes('-layout-'));
 await page.getByRole('combobox',{name:'요청 선택',exact:true}).fill(empty.id);
 await page.getByRole('option',{name:new RegExp('^'+empty.id+' ·')}).click();
 await expect(page.getByRole('combobox',{name:'실행 선택',exact:true})).toBeDisabled();
 await page.screenshot({path:out+'/captures/stale-flow.png',fullPage:true});
 await expect(page.locator('.obs-node')).toHaveCount(0);
});
test('playback is read only and trace opens',async({page})=>{
 await login(page,'operator');const active=await activeRun(page);await page.goto(`/observatory?run_id=${active.run}`);await expect(page.locator('.obs-node').first()).toBeVisible();
 const mutations:string[]=[];page.on('request',r=>{if(r.url().includes('/api/')&&!['GET','HEAD'].includes(r.method()))mutations.push(r.method()+' '+r.url());});
 await page.getByRole('button',{name:'재생',exact:true}).click();await page.getByRole('button',{name:'전체 결과',exact:true}).click();
 await page.locator('.obs-node').first().click();const drawer=page.getByRole('dialog',{name:'Trace 상세'});await expect(drawer).toContainText('오류 분류');await expect(drawer).toContainText('실행 버전');
 await page.screenshot({path:out+'/captures/trace.png',fullPage:true});expect(mutations).toEqual([]);
});
test('real judgment map navigation and details',async({page,context})=>{
 await login(page,'reviewer');const active=await activeRun(page);const graph=await(await page.request.get(`/api/graph/judgment?request_id=${active.id}`)).json();
 expect(graph.nodes.length).toBeGreaterThan(0);await page.goto(`/judgment-map?request_id=${active.id}`);await expect(page.getByTestId('jm-board')).toHaveAttribute('data-node-count',String(graph.node_count));
 const before=await page.getByTestId('jm-zoom-pct').innerText();await page.getByRole('button',{name:'확대',exact:true}).click();await expect(page.getByTestId('jm-zoom-pct')).not.toHaveText(before);
 await page.getByRole('button',{name:'축소',exact:true}).click();await page.getByRole('button',{name:'전체 보기',exact:true}).click();
 await page.getByRole('button',{name:'크게 보기',exact:true}).click();await expect(page.locator('.jm-page')).toHaveClass(/is-expanded/);await page.keyboard.press('Escape');await expect(page.locator('.jm-page')).not.toHaveClass(/is-expanded/);
 await page.getByRole('button',{name:'목록 보기',exact:true}).click();await expect(page.locator('.jm-item')).toHaveCount(graph.node_count);
 await page.locator('.jm-item').first().focus();await page.keyboard.press('ArrowRight');await page.keyboard.press('Enter');await expect(page.getByTestId('jm-detail')).toBeVisible();
 await context.grantPermissions(['clipboard-read','clipboard-write']);await page.getByRole('button',{name:'ID 복사'}).click();await expect(page.getByRole('button',{name:'ID 복사'})).toHaveText('복사됨');
 await page.screenshot({path:out+'/captures/map-detail.png',fullPage:true});
 const evidence=page.locator('.jm-item[data-kind="EvidenceSpan"]').first();if(await evidence.count()){await evidence.click();await page.getByRole('button',{name:'원문 열기',exact:true}).click();await expect(page.getByRole('dialog')).toBeVisible();await page.screenshot({path:out+'/captures/map-source.png',fullPage:true});}
});
test('map source location resolves with source reader',async({page})=>{
 await login(page,'source_reader');const active=await activeRun(page);await page.goto(`/judgment-map?request_id=${active.id}`);await expect(page.getByTestId('jm-board')).toBeVisible();
 await page.getByRole('button',{name:'목록 보기',exact:true}).click();await page.locator('.jm-item[data-kind="EvidenceSpan"]').first().click();await page.getByRole('button',{name:'원문 열기',exact:true}).click();
 await expect(page.getByTestId('ev-scroll')).toBeVisible();await expect(page.getByTestId('ev-scroll')).toContainText('이상반응');await page.screenshot({path:out+'/captures/map-source-resolved.png',fullPage:true});
});
