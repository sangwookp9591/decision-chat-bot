import {test,expect, type Page} from '../../../../../frontend/node_modules/@playwright/test';
import {submitApi,waitJudged,pendingReview,tenant,password} from '../../../../../frontend/e2e/acceptance/helpers';
import {actor,watch} from './telemetry';
import {join} from 'node:path';
const base=process.env.E2E_BASE_URL!;
const out=process.env.ACC_UI_OUT!;
test.setTimeout(120000);
test.beforeEach(async({page})=>watch(page));
async function shot(page:Page,name:string){await page.screenshot({path:join(out,`${test.info().project.name}-${name}.png`),fullPage:true})}
test('QA-A UI login wrong password keyboard login and logout',async({page})=>{
 await page.goto('/');
 await page.getByLabel('이메일').fill(`requester@${tenant}.dev`);
 await page.getByLabel('암호',{exact:true}).fill('incorrect-qa-password');
 await page.getByRole('button',{name:'로그인',exact:true}).press('Enter');
 await expect(page.getByRole('alert')).toBeVisible();
 await shot(page,'wrong-password');
 await page.getByLabel('암호',{exact:true}).fill(password);
 await page.getByLabel('암호',{exact:true}).press('Enter');
 await expect(page.getByRole('heading',{name:'안녕하세요, 일동이예요'})).toBeVisible();
 await page.getByRole('button',{name:'로그아웃'}).first().press('Enter');
 await expect(page.getByLabel('이메일')).toBeVisible();
});
test('QA-A chips Shift Enter synthetic IME and Enter send',async({browser})=>{
 const a=await actor(browser,base,'requester');const p=a.page;await p.goto('/');
 await p.getByRole('group',{name:'예시 요청'}).getByRole('button').first().press('Enter');
 const input=p.getByLabel('요청 내용');await expect(input).not.toHaveValue('');
 await input.fill('회의실 예약');await input.press('End');await input.press('Shift+Enter');await p.keyboard.insertText('가');
 expect(await input.inputValue()).toContain('\n');
 await input.dispatchEvent('keydown',{key:'Enter',code:'Enter',isComposing:true,keyCode:229});
 await expect(p).not.toHaveURL(/request_id=/);
 await input.fill('사내 회의실 조회 화면 QA 입력 시험');
 const response=p.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/api/requests'));
 await input.press('Enter');expect((await response).status()).toBe(202);
 await expect(p.locator('.result-stack:not(.provisional-result)')).toBeVisible({timeout:90000});
 await shot(p,'keyboard-result');await a.ctx.close();
});
test('QA-A attachment six files capped and oversized upload rejected',async({browser})=>{
 const a=await actor(browser,base,'requester');const p=a.page;await p.goto('/');
 await p.getByLabel('파일 첨부').setInputFiles(Array.from({length:6},(_,i)=>({name:`file-${i}.md`,mimeType:'text/markdown',buffer:Buffer.from('예약 내용')})));
 await expect(p.getByRole('list',{name:'첨부할 파일'}).locator('li')).toHaveCount(5);
 await expect(p.getByText(/앞에서부터 5개/)).toBeVisible();
 for(let i=0;i<5;i++)await p.getByRole('button',{name:`file-${i}.md 첨부 제거`}).click();
 await p.getByLabel('요청 내용').fill('용량 초과 파일 시험');
 await p.getByLabel('파일 첨부').setInputFiles({name:'oversize.md',mimeType:'text/markdown',buffer:Buffer.alloc(10*1024*1024+1,97)});
 const response=p.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/api/requests'));
 await p.getByRole('button',{name:'요청 보내기'}).click();expect((await response).status()).toBe(202);
 await expect(p.getByRole('group',{name:'읽기 실패 파일'})).toContainText('oversize.md');
 await shot(p,'oversize');await a.ctx.close();
});
async function approved(browser:any){
 const rq=await actor(browser,base,'requester');const rv=await actor(browser,base,'reviewer');
 const id=await submitApi(rq,'E2E_AUTO_ASSIGN 사내 보고서를 시스템과 연동하여 조회하는 업무 '+Date.now());
 await waitJudged(rq,id);const review=await pendingReview(rv,id);
 await rv.page.goto(`/review?review_id=${review.id}`);
 const decision=rv.page.waitForResponse(r=>r.url().includes('/decision')&&r.request().method()==='POST');
 await rv.page.getByRole('button',{name:'승인',exact:true}).click();
 expect((await decision).status()).toBe(200);
 await expect(rv.page.getByRole('status')).toContainText('결정을 저장했습니다');
 const tasks=(await (await rv.api.get(`/api/tasks?request_id=${id}`)).json()).tasks;
 const target=tasks.find((t:any)=>t.status==='대기');expect(target).toBeTruthy();
 await rq.ctx.close();await rv.ctx.close();return target;
}
test('QA-A task lifecycle filters permission and refresh',async({browser})=>{
 const target=await approved(browser);const a=await actor(browser,base,'team_member');const p=a.page;
 await p.goto('/tasks');await p.locator('.task-list button',{hasText:target.id}).click();
 await p.getByRole('button',{name:'진행으로 변경'}).click();await expect(p.getByRole('button',{name:'완료로 변경'})).toBeVisible();
 const completed=p.waitForResponse(r=>r.url().includes('/transition')&&r.request().method()==='POST');
 await p.getByRole('button',{name:'완료로 변경'}).click();expect((await completed).status()).toBe(200);await expect(p.getByRole('button',{name:'완료로 변경'})).toHaveCount(0);await expect(p.getByRole('status')).toContainText('업무 상태를 갱신했습니다');
 await p.reload();await p.getByLabel('상태',{exact:true}).selectOption('완료');await expect(p.locator('.task-list button',{hasText:target.id})).toBeVisible();
 for(const [label,value] of [['역할','lead'],['방식',target.method]]){await p.getByLabel(label,{exact:true}).selectOption(value);await expect(p.locator('.task-list button',{hasText:target.id})).toBeVisible();}
 await shot(p,'task-complete');const rq=await actor(browser,base,'requester');
 const r=await rq.api.post(`/api/tasks/${target.id}/transition`,{headers:{'X-CSRF-Token':await rq.csrf()},data:{to:'진행',expected_status:'완료'}});
 expect([403,404]).toContain(r.status());await rq.ctx.close();await a.ctx.close();
});
test('QA-A candidate task detail Escape closes keyboard dialog',async({browser})=>{
 const target=await approved(browser);const a=await actor(browser,base,'team_member');const p=a.page;await p.goto('/tasks');
 const row=p.locator('.task-list button',{hasText:target.id});await row.press('Enter');await expect(p.getByRole('dialog',{name:'업무 상세'})).toBeVisible();
 await p.keyboard.press('Escape');await shot(p,'task-escape');await expect(p.getByRole('dialog',{name:'업무 상세'})).toHaveCount(0);await a.ctx.close();
});
test('QA-A candidate task update in second tab appears without reload',async({browser})=>{
 const target=await approved(browser);const a=await actor(browser,base,'team_member');const p=a.page;const second=await a.ctx.newPage();
 await p.goto('/tasks');await second.goto('/tasks');
 await p.locator('.task-list button',{hasText:target.id}).click();
 await second.locator('.task-list button',{hasText:target.id}).click();await second.getByRole('button',{name:'진행으로 변경'}).click();
 await expect(second.getByRole('button',{name:'완료로 변경'})).toBeVisible();
 await shot(p,'task-other-tab-before');
 await expect(p.getByRole('button',{name:'완료로 변경'})).toBeVisible({timeout:15000});await a.ctx.close();
});
test('QA-A reviewer reason mandatory and simultaneous conflict',async({browser})=>{
 const rq=await actor(browser,base,'requester');const rv=await actor(browser,base,'reviewer');const other=await actor(browser,base,'reviewer');
 const id=await submitApi(rq,'검토자 경합 시험 '+Date.now());await waitJudged(rq,id);const review=await pendingReview(rv,id);
 for(const a of [rv,other]){await a.page.goto(`/review?review_id=${review.id}`);await expect(a.page.getByRole('button',{name:'반려',exact:true})).toBeDisabled();await expect(a.page.getByRole('button',{name:'정보 요청',exact:true})).toBeDisabled();await a.page.getByLabel('결정 사유').fill('중복 판단 방지 시험 사유');}
 const responses=await Promise.all([rv,other].map(async a=>{const response=a.page.waitForResponse(r=>r.url().includes('/decision')&&r.request().method()==='POST');await a.page.getByRole('button',{name:'반려',exact:true}).click();return (await response).status()}));
 expect([...responses].sort()).toEqual([200,409]);const loser=responses[0]===409?rv:other;
 await expect(loser.page.getByRole('status')).toContainText('다른 검토자가 먼저 변경했습니다');await shot(loser.page,'review-conflict');
 await Promise.all([rq,rv,other].map(a=>a.ctx.close()));
});
for(const role of ['requester','reviewer','team_member'])for(const width of [1440,375])for(const theme of ['light','dark'] as const){
 test(`QA-A visual ${role} ${width} ${theme}`,async({browser})=>{
 const a=await actor(browser,base,role);const p=a.page;await p.setViewportSize({width,height:900});await p.emulateMedia({colorScheme:theme});
 await p.goto(role==='requester'?'/':role==='reviewer'?'/review':'/tasks');
 await expect(p.getByRole('heading',{name:role==='requester'?'안녕하세요, 일동이예요':role==='reviewer'?'검토 대기':'업무',exact:true})).toBeVisible();await p.keyboard.press('Tab');
 await shot(p,`visual-${role}-${width}-${theme}`);expect(await p.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);await a.ctx.close();
 });
}
test('QA-A candidate team filter retains tasks assigned to IT',async({browser})=>{
 const target=await approved(browser);const a=await actor(browser,base,'team_member');const p=a.page;
 const tasks=(await (await a.api.get(`/api/tasks?request_id=${target.request_id}`)).json()).tasks;
 const it=tasks.find((t:any)=>t.lead_org===`${tenant}-it`||t.lead_org==='IT팀');expect(it,'IT assigned fixture').toBeTruthy();
 await p.goto('/tasks');await expect(p.locator('.task-list button',{hasText:it.id})).toBeVisible();
 await p.getByLabel('팀',{exact:true}).selectOption('IT팀');await shot(p,'team-filter');
 await expect(p.locator('.task-list button',{hasText:it.id})).toBeVisible();await a.ctx.close();
});
test('QA-A candidate reviewer queue receives other role submission without reload',async({browser})=>{
 const rq=await actor(browser,base,'requester');const rv=await actor(browser,base,'reviewer');await rv.page.goto('/review');
 await expect(rv.page.getByRole('heading',{name:'검토 대기',exact:true})).toBeVisible();
 const id=await submitApi(rq,'다른 역할 실시간 검토 목록 확인 '+Date.now());await waitJudged(rq,id);await pendingReview(rv,id);
 await shot(rv.page,'review-sse');await expect(rv.page.locator('nav[aria-label="검토 대기 목록"] button',{hasText:id})).toBeVisible({timeout:15000});
 await rq.ctx.close();await rv.ctx.close();
});
test('QA-A real predecessor blocks then unlocks task after completion',async({browser})=>{
 const rq=await actor(browser,base,'requester');const rv=await actor(browser,base,'reviewer');const a=await actor(browser,base,'team_member');
 const id=await submitApi(rq,'E2E_AUTO_ASSIGN 시설 점검 보고서와 연동이 필요합니다 '+Date.now());await waitJudged(rq,id);const review=await pendingReview(rv,id);
 await rv.page.goto(`/review?review_id=${review.id}`);await rv.page.getByRole('button',{name:'승인',exact:true}).click();await expect(rv.page.getByRole('status')).toContainText('결정을 저장했습니다');
 const list=async()=>(await (await a.api.get(`/api/tasks?request_id=${id}`)).json()).tasks;
 const initial=await list();const blocked=initial.find((t:any)=>!t.can_start&&t.predecessor_tasks.length>0);expect(blocked,'real predecessor fixture').toBeTruthy();
 await a.page.goto('/tasks');await a.page.locator('.task-list button',{hasText:blocked.id}).click();await expect(a.page.getByRole('button',{name:'진행으로 변경'})).toBeDisabled();await shot(a.page,'predecessor-blocked');
 await a.page.getByRole('button',{name:'닫기',exact:true}).click();
 for(let step=0;step<initial.length;step++){
 const rows=await list();if(rows.find((t:any)=>t.id===blocked.id).can_start)break;
 const ready=rows.find((t:any)=>t.can_start&&t.status==='대기');expect(ready,'unfinished predecessor can start').toBeTruthy();
 await a.page.locator('.task-list button',{hasText:ready.id}).click();await a.page.getByRole('button',{name:'진행으로 변경'}).click();await a.page.getByRole('button',{name:'완료로 변경'}).click();await a.page.getByRole('button',{name:'닫기',exact:true}).click();
 }
 await a.page.getByRole('button',{name:'새로고침',exact:true}).click();await a.page.locator('.task-list button',{hasText:blocked.id}).click();await expect(a.page.getByRole('button',{name:'진행으로 변경'})).toBeEnabled();await shot(a.page,'predecessor-unlocked');
 await Promise.all([rq,rv,a].map(x=>x.ctx.close()));
});
