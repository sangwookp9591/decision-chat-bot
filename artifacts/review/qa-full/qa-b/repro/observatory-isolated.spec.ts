import {test,expect} from '../../../../../frontend/node_modules/@playwright/test/index.mjs';
import {resolve} from 'node:path';
// Explicit HTTP fixture isolates the UI from shared DB outage. Shapes reuse Observatory.test.tsx.
async function fixture(page:any){
 await page.route(/http:\/\/127\.0\.0\.1:8791\/api\//,async(route:any)=>{
  const path=new URL(route.request().url()).pathname;let body:any={};
  if(path==='/api/auth/me')body={user_id:'qa-b-operator',tenant_id:'qa-b-fixture',roles:['operator'],mode:'mock'};
  else if(path==='/api/requests')body={items:[{id:'req_A',status:'completed'},{id:'req_B',status:'취소됨'}]};
  else if(path==='/api/requests/req_A/runs')body={active_run_id:'run_A',runs:[{id:'run_A',status:'succeeded'}]};
  else if(path==='/api/requests/req_B/runs')body={active_run_id:null,runs:[]};
  else if(path.endsWith('/flow'))body={request_id:'req_A',run_id:'run_A',live:false,nodes:[{id:'step_A',kind:'code',name:'A 요청 입력 정리',status:'succeeded',duration_ms:100}],edges:[]};
  else if(path.endsWith('/playback'))body={request_id:'req_A',run_id:'run_A',live:false,events:[],final_result:'succeeded',reviews:[]};
  else if(path.includes('/steps/'))body={id:'step_A',run_id:'run_A',kind:'code',name:'A 요청 입력 정리',status:'succeeded',duration_ms:100,config_version:1,versions:{schema:1},started_at:'2026-10-05T00:00:00Z',ended_at:'2026-10-05T00:00:00.100Z'};
  await route.fulfill({json:body});
 });
}
test('QA-B-03 empty request selection must clear previous flow',async({page})=>{
 await fixture(page);await page.goto('/observatory?request_id=req_A&run_id=run_A');await expect(page.locator('.obs-node')).toHaveCount(1);
 await page.getByRole('combobox',{name:'요청 선택',exact:true}).fill('req_B');await page.getByRole('option',{name:/req_B/}).click();
 await expect(page.getByRole('combobox',{name:'실행 선택',exact:true})).toBeDisabled();
 await page.screenshot({path:resolve('../artifacts/review/qa-full/qa-b/captures/stale-flow-isolated.png'),fullPage:true});
 await expect(page.locator('.obs-node')).toHaveCount(0);
});
test('fixture playback has no mutation and trace has duration version',async({page})=>{
 await fixture(page);await page.goto('/observatory?request_id=req_A&run_id=run_A');await expect(page.locator('.obs-node')).toHaveCount(1);
 const mutations:string[]=[];page.on('request',r=>{if(r.url().includes('/api/')&&!['GET','HEAD'].includes(r.method()))mutations.push(r.method());});
 await page.getByRole('button',{name:'재생',exact:true}).click();await page.getByRole('button',{name:'전체 결과',exact:true}).click();await page.locator('.obs-node').click();
 await expect(page.getByRole('dialog')).toContainText('100 ms');await expect(page.getByRole('dialog')).toContainText('설정 v1');expect(mutations).toEqual([]);
});
