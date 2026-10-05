import {test,expect} from '@playwright/test';
import {submitApi,waitJudged,pendingReview,actor} from './acceptance/helpers';
const base=process.env.E2E_BASE_URL!;
test.setTimeout(120000);

async function approvedTask(browser:any){
 const requester=await actor(browser,base,'requester');const reviewer=await actor(browser,base,'reviewer');
 const requestId=await submitApi(requester,`E2E_AUTO_ASSIGN 사내 보고서를 시스템과 연동하여 조회하는 업무 ${Date.now()}`);await waitJudged(requester,requestId);const review=await pendingReview(reviewer,requestId);
 await reviewer.page.goto(`/review?review_id=${review.id}`);await reviewer.page.getByRole('button',{name:'승인',exact:true}).click();await expect(reviewer.page.getByRole('status')).toContainText('결정을 저장했습니다');
 const tasks=(await (await requester.api.get(`/api/tasks?request_id=${requestId}`)).json()).tasks;const target=tasks.find((item:any)=>item.request_id===requestId&&item.status==='대기'&&item.can_start);expect(target).toBeTruthy();
 await Promise.all([requester.ctx.close(),reviewer.ctx.close()]);return target;
}

test('task detail closes on Escape and restores focus',async({browser})=>{
 const task=await approvedTask(browser);const user=await actor(browser,base,'team_member');const page=user.page;await page.goto('/tasks');const row=page.locator('.task-list button',{hasText:task.id});await row.press('Enter');await expect(page.getByRole('dialog',{name:'업무 상세'})).toBeVisible();await page.keyboard.press('Escape');await expect(page.getByRole('dialog',{name:'업무 상세'})).toHaveCount(0);await expect(row).toBeFocused();await user.ctx.close();
});

test('task update in second tab refreshes list and selected detail',async({browser})=>{
 const task=await approvedTask(browser);const user=await actor(browser,base,'team_member');const first=user.page;const second=await user.ctx.newPage();
 await first.goto('/tasks');await second.goto('/tasks');await first.locator('.task-list button',{hasText:task.id}).click();await second.locator('.task-list button',{hasText:task.id}).click();await second.getByRole('button',{name:'진행으로 변경'}).click();
 await expect(first.getByRole('button',{name:'완료로 변경'})).toBeVisible({timeout:15000});await expect(first.locator('.task-list button',{hasText:task.id})).toContainText('진행');await user.ctx.close();
});

test('review queue receives another role submission without reload',async({browser})=>{
 const requester=await actor(browser,base,'requester');const reviewer=await actor(browser,base,'reviewer');await reviewer.page.goto('/review');
 const requestId=await submitApi(requester,`QA-A2 실시간 검토 대기 ${Date.now()}`);await waitJudged(requester,requestId);await pendingReview(reviewer,requestId);
 await expect(reviewer.page.locator('nav[aria-label="검토 대기 목록"] button',{hasText:requestId})).toBeVisible({timeout:15000});await Promise.all([requester.ctx.close(),reviewer.ctx.close()]);
});
