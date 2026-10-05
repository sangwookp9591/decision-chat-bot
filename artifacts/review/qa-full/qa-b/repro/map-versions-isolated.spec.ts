import {test,expect} from '../../../../../frontend/node_modules/@playwright/test/index.mjs';
import {resolve} from 'node:path';
// Same saved-relation fixture as frontend/src/pages/judgment-map/versionTabs.test.tsx.
const node=(id:string,kind:string,layer:number,extra={})=>({id,kind,layer,title:id,summary:'',status:null,actor:null,at:null,version:null,source:null,request_id:'req1',refs:{request_id:'req1'},...extra});
const rv=(n:number,status:string)=>node(`rv${n}`,'RuleVersion',4,{status,version:`R-X-01@${n}`,refs:{rule_id:'R-X-01',rule_version:`rv${n}`}});
const edge=(type:string,up:string,down:string)=>({id:`${type}:${down}->${up}`,type,source:down,target:up,upstream:up,downstream:down});
const nodes=[node('c1','Correction',1),node('c2','Correction',1),node('dec1','RuleDecision',3),node('dec2','RuleDecision',3),rv(3,'validating'),rv(1,'reverted'),rv(2,'published'),node('s1','RunStep',5),node('s2','RunStep',5),node('lone','Correction',1)];
const edges=[edge('DECIDES','c1','dec1'),edge('DERIVED_FROM','dec1','rv1'),edge('APPLIED','rv1','s1'),edge('DECIDES','c2','dec2'),edge('DERIVED_FROM','dec2','rv2'),edge('APPLIED','rv2','s2')];
test('rule version tabs scope the rendered stored relations',async({page})=>{
 await page.route(/http:\/\/127\.0\.0\.1:8791\/api\//,async route=>{
  const path=new URL(route.request().url()).pathname;
  const body=path==='/api/auth/me'?{user_id:'qa-b-reviewer',roles:['reviewer'],tenant_id:'qa-b-fixture',mode:'mock'}:{nodes,edges,layers:[1,2,3,4,5].map(layer=>({layer,name:`계층${layer}`,desc:'',count:nodes.filter(n=>n.layer===layer).length})),truncated:false,node_count:nodes.length,edge_count:edges.length};
  await route.fulfill({json:body});
 });
 await page.goto('/judgment-map?rule_id=R-X-01');const summary=page.getByTestId('jm-summary');await expect(summary).toContainText('노드 10개 · 연결 6개');
 await page.getByRole('tab',{name:/v2/}).click();await expect(summary).toContainText('노드 4개 · 연결 3개');await expect(page.getByRole('tab',{name:/v2/})).toHaveAttribute('aria-selected','true');
 await page.getByRole('tab',{name:/v3/}).click();await expect(summary).toContainText('노드 1개 · 연결 0개');
 await page.getByRole('tab',{name:'전체',exact:true}).click();await expect(summary).toContainText('노드 10개 · 연결 6개');
 await page.screenshot({path:resolve('../artifacts/review/qa-full/qa-b/captures/map-versions-fixture.png'),fullPage:true});
});
