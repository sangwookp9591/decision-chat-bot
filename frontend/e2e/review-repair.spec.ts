import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {resolve} from 'node:path';

const tenant=`t-review-repair-${process.pid}`;
const python=resolve('../backend/.venv/bin/python');
const backend=resolve('../backend');
const runPython=(code:string)=>execFileSync(python,['-c',code],{cwd:backend,encoding:'utf8',env:{...process.env,JEVTRIAGE_STRICT_TENANT:'1'}});
let reviewId:string;
test.beforeAll(()=>{
 const output=runPython(`import sys,asyncio,json
sys.path[:0]=['tests/acceptance','tests/integration']
from provision import provision
from test_review_assignment import sample,make_undetermined
from jevtriage.db.driver import close_driver
async def main():
 await provision(('${tenant}',))
 _,review,command=await sample('${tenant}')
 await make_undetermined('${tenant}',command['run_id'])
 print(json.dumps({'review_id':review}))
 await close_driver()
asyncio.run(main())`);
 reviewId=JSON.parse(output.trim().split('\n').at(-1)!).review_id;
});
test.afterAll(()=>runPython(`import asyncio
from jevtriage.db.tx import write_tx
from jevtriage.db.driver import close_driver
async def main():
 async def clear(tx):
  await (await tx.run('MATCH (n {tenant_id:$tenant}) DETACH DELETE n',tenant='${tenant}')).consume()
 await write_tx('${tenant}',clear)
 await close_driver()
asyncio.run(main())`));

test('P1-01 repairs an undetermined draft and approves the final version with HTTP 200',async({page})=>{
 const login=await page.request.post('/api/auth/login',{data:{email:`reviewer@${tenant}.dev`,password:'dev-only-change-me'}});
 expect(login.status()).toBe(200);
 await page.goto(`/review?review_id=${reviewId}`);
 // Unchanged approval names every unresolved field, without consuming the review.
 const invalid=page.waitForResponse(r=>r.url().includes('/decision')&&r.request().method()==='POST');
 await page.getByRole('button',{name:'승인',exact:true}).click();
 expect((await invalid).status()).toBe(422);
 await expect(page.getByLabel('업무 방식',{exact:true})).toHaveAttribute('aria-invalid','true');
 await page.getByLabel('개발 가능성 수정').fill('가능');
 await page.getByLabel('주관 조직',{exact:true}).selectOption(`${tenant}-it`);
 await page.getByLabel('업무 방식',{exact:true}).selectOption('일반 기술');
 await page.getByLabel('업무 제목',{exact:true}).fill('미정 초안 보완 업무');
 await page.getByLabel('산출물',{exact:true}).fill('검토 완료 결과');
 await page.getByLabel('결정 사유',{exact:true}).fill('미정 필드를 보완하여 승인');
 const decision=page.waitForResponse(r=>r.url().includes('/decision')&&r.request().method()==='POST');
 await page.getByRole('button',{name:'수정 승인',exact:true}).click();
 const response=await decision;
 expect(response.status(),await response.text()).toBe(200);
 expect(await response.json()).toMatchObject({status:'approved',draft_version:2});
 await expect(page.getByText('결정을 저장했습니다. 업무 목록을 새로 고칩니다.')).toBeVisible();
 const detail=await (await page.request.get(`/api/reviews/${reviewId}`)).json();
 expect(detail.original_draft.tasks[0]).toMatchObject({method:'미정',lead_org:'미정'});
 expect(detail.current_draft.tasks[0]).toMatchObject({method:'일반 기술',lead_org:`${tenant}-it`,deliverable:'검토 완료 결과'});
 expect(detail.history).toHaveLength(1);
});
