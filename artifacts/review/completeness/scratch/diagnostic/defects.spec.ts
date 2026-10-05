import {test,expect} from '@playwright/test';
const tenant='t-audit-e2e-1005';
async function login(page:any,role:string){const r=await page.request.post('/api/auth/login',{data:{email:`${role}@${tenant}.dev`,password:'dev-only-change-me'}});expect(r.status()).toBe(200);}
test('AUDIT-P1-01 a reviewer can repair an undetermined draft before approval',async({page})=>{
 await login(page,'reviewer');await page.goto('/review?request_id=req_33a60302a76c4b96906b01cdf11aab4e');
 await page.getByLabel('개발 가능성 수정').fill('가능');await page.getByLabel('주관 조직',{exact:true}).fill('IT팀');await page.getByLabel('결정 사유',{exact:true}).fill('감사 재현: 업무 담당 조직을 올바르게 수정한 뒤 승인합니다.');
 const response=page.waitForResponse(r=>r.url().includes('/decision')&&r.request().method()==='POST');await page.getByRole('button',{name:'수정 승인',exact:true}).click();const r=await response;expect(r.status(),await r.text()).toBe(200);
});
test('AUDIT-P1-02 completed confirmation enables the main task start button',async({page})=>{
 await login(page,'team_member');await page.goto('/tasks');await page.locator('.task-list button',{hasText:'감사 시드: 확인 완료 후 시작'}).click();
 const dialog=page.getByRole('dialog',{name:'업무 상세'});await expect(dialog).toContainText('감사 시드: 완료된 사전 확인 · 완료');await expect(dialog.getByRole('button',{name:'진행으로 변경'})).toBeEnabled();
});
