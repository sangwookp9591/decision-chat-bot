import {test,expect} from '../../../../../frontend/node_modules/@playwright/test';
import {actor} from './telemetry';
import {submitApi,waitJudged,pendingReview} from '../../../../../frontend/e2e/acceptance/helpers';
import {join} from 'node:path';
test('QA-A review status filters retain each decision and closed records disable decisions',async({browser})=>{
 test.setTimeout(120000);
 const rq=await actor(browser,process.env.E2E_BASE_URL!,'requester');
 const rv=await actor(browser,process.env.E2E_BASE_URL!,'reviewer');
 for(const [label,status] of [['승인','approved'],['반려','rejected'],['정보 요청','info_requested']]){
  const id=await submitApi(rq,'검토 필터 확인 '+label+' '+Date.now());await waitJudged(rq,id);const review=await pendingReview(rv,id);
  await rv.page.goto(`/review?review_id=${review.id}`);await rv.page.getByLabel('결정 사유').fill('상태 필터 여정 검증');
  await rv.page.getByRole('button',{name:label,exact:true}).click();await expect(rv.page.getByRole('status')).toContainText('결정을 저장했습니다');
  await rv.page.getByRole('combobox',{name:'검토 상태 필터'}).selectOption(status);
  const row=rv.page.locator('nav[aria-label="검토 대기 목록"] button',{hasText:id});await expect(row).toBeVisible();await row.click();
  await expect(rv.page.getByRole('note').filter({hasText:'이미 처리된 검토'})).toBeVisible();
  for(const name of ['승인','수정 승인','반려','정보 요청'])await expect(rv.page.getByRole('button',{name,exact:true})).toBeDisabled();
  await rv.page.screenshot({path:join(process.env.ACC_UI_OUT!,`${test.info().project.name}-filter-${status}.png`),fullPage:true});
 }
 await rq.ctx.close();await rv.ctx.close();
});
