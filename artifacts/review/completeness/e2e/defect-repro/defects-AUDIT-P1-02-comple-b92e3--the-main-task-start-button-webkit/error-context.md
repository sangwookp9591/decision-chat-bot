# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: defects.spec.ts >> AUDIT-P1-02 completed confirmation enables the main task start button
- Location: artifacts/review/completeness/scratch/diagnostic/defects.spec.ts:9:5

# Error details

```
Error: expect(locator).toBeEnabled() failed

Locator:  getByRole('dialog', { name: '업무 상세' }).getByRole('button', { name: '진행으로 변경' })
Expected: enabled
Received: disabled
Timeout:  5000ms

Call log:
  - Expect "toBeEnabled" getByRole('dialog', { name: '업무 상세' }).getByRole('button', { name: '진행으로 변경' }) with timeout 5000ms
  - waiting for getByRole('dialog', { name: '업무 상세' }).getByRole('button', { name: '진행으로 변경' })
    14 × locator resolved to <button disabled class="ui-button secondary" aria-describedby="task-block-why">진행으로 변경</button>
       - unexpected value "disabled"

```

```yaml
- button "진행으로 변경" [disabled]
```

# Test source

```ts
  1  | import {test,expect} from '@playwright/test';
  2  | const tenant='t-audit-e2e-1005';
  3  | async function login(page:any,role:string){const r=await page.request.post('/api/auth/login',{data:{email:`${role}@${tenant}.dev`,password:'dev-only-change-me'}});expect(r.status()).toBe(200);}
  4  | test('AUDIT-P1-01 a reviewer can repair an undetermined draft before approval',async({page})=>{
  5  |  await login(page,'reviewer');await page.goto('/review?request_id=req_33a60302a76c4b96906b01cdf11aab4e');
  6  |  await page.getByLabel('개발 가능성 수정').fill('가능');await page.getByLabel('주관 조직',{exact:true}).fill('IT팀');await page.getByLabel('결정 사유',{exact:true}).fill('감사 재현: 업무 담당 조직을 올바르게 수정한 뒤 승인합니다.');
  7  |  const response=page.waitForResponse(r=>r.url().includes('/decision')&&r.request().method()==='POST');await page.getByRole('button',{name:'수정 승인',exact:true}).click();const r=await response;expect(r.status(),await r.text()).toBe(200);
  8  | });
  9  | test('AUDIT-P1-02 completed confirmation enables the main task start button',async({page})=>{
  10 |  await login(page,'team_member');await page.goto('/tasks');await page.locator('.task-list button',{hasText:'감사 시드: 확인 완료 후 시작'}).click();
> 11 |  const dialog=page.getByRole('dialog',{name:'업무 상세'});await expect(dialog).toContainText('감사 시드: 완료된 사전 확인 · 완료');await expect(dialog.getByRole('button',{name:'진행으로 변경'})).toBeEnabled();
     |                                                                                                                                                                             ^ Error: expect(locator).toBeEnabled() failed
  12 | });
  13 | 
```