import {test,expect} from '../../../../../frontend/node_modules/@playwright/test';
import {tenant,password} from '../../../../../frontend/e2e/acceptance/helpers';
import {actor,watch} from './telemetry';
import {execFileSync} from 'node:child_process';
import {resolve,join} from 'node:path';
const base=process.env.E2E_BASE_URL!;
test.setTimeout(90000);
test.beforeEach(async({page})=>watch(page));
test('QA-A account locks after ten incorrect passwords',async({page,browserName})=>{
 const email=`${browserName==='chromium'?'requester':'team_member'}@${tenant}b.dev`;
 await page.goto('/');await page.getByLabel('이메일').fill(email);await page.getByLabel('암호',{exact:true}).fill('qa-invalid');
 for(let i=0;i<10;i++){
 const response=page.waitForResponse(r=>r.url().endsWith('/api/auth/login'));
 await page.getByRole('button',{name:'로그인',exact:true}).click();expect((await response).status()).toBe(401);
 }
 await page.getByLabel('암호',{exact:true}).fill(password);const response=page.waitForResponse(r=>r.url().endsWith('/api/auth/login'));
 await page.getByRole('button',{name:'로그인',exact:true}).click();expect((await response).status()).toBe(429);
 await expect(page.getByRole('alert')).toBeVisible();await page.screenshot({path:join(process.env.ACC_UI_OUT!,`${browserName}-locked.png`)});
});
test('QA-A long text exceeds 20000 character contract safely',async({browser})=>{
 const a=await actor(browser,base,'requester');const p=a.page;await p.goto('/');
 await p.getByLabel('요청 내용').fill('가'.repeat(20001));const response=p.waitForResponse(r=>r.url().endsWith('/api/requests')&&r.request().method()==='POST');
 await p.getByRole('button',{name:'요청 보내기'}).click();expect((await response).status()).toBe(400);
 await expect(p.getByLabel('요청 내용')).toHaveValue('가'.repeat(20001));await expect(p).not.toHaveURL(/request_id/);await p.screenshot({path:join(process.env.ACC_UI_OUT!,`${test.info().project.name}-long-input.png`)});await a.ctx.close();
});
for(const kind of ['encrypted','disguised'] as const)test(`QA-A ${kind} file requires exclusion`,async({browser})=>{
 const a=await actor(browser,base,'requester');const p=a.page;await p.goto('/');
 const buffer=kind==='encrypted'?execFileSync(resolve('../backend/.venv/bin/python'),['-c',"import sys,io;from pypdf import PdfWriter;w=PdfWriter();w.add_blank_page(width=200,height=200);w.encrypt('qa-fixture-only');b=io.BytesIO();w.write(b);sys.stdout.buffer.write(b.getvalue())"]):Buffer.from('PK pretending to be a PDF but not one');
 await p.getByLabel('파일 첨부').setInputFiles({name:`${kind}.pdf`,mimeType:'application/pdf',buffer});await p.getByLabel('요청 내용').fill('첨부 오류 안내 확인');
 await p.getByRole('button',{name:'요청 보내기'}).click();await expect(p.getByRole('group',{name:'읽기 실패 파일'})).toContainText(`${kind}.pdf`,{timeout:30000});
 await p.screenshot({path:join(process.env.ACC_UI_OUT!,`${test.info().project.name}-${kind}.png`)});await p.getByRole('button',{name:'제외하고 진행'}).click();
 await expect(p.locator('.result-stack:not(.provisional-result)')).toBeVisible({timeout:60000});await a.ctx.close();
});
