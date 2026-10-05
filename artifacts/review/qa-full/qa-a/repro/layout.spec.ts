import {test,expect} from '../../../../../frontend/node_modules/@playwright/test';
import {actor} from './telemetry';
import {writeFileSync} from 'node:fs';
import {join} from 'node:path';
test('QA-A provisional to final exact zero pixel positions and copy',async({browser,browserName})=>{
 test.setTimeout(90000);const a=await actor(browser,process.env.E2E_BASE_URL!,'requester');const p=a.page;
 if(browserName==='chromium')await a.ctx.grantPermissions(['clipboard-read','clipboard-write']);
 await p.bringToFront();await p.setViewportSize({width:1440,height:900});await p.goto('/');
 await p.evaluate(()=>{
 const state={before:null as any,after:null as any};(window as any).__qaLayout=state;
 const snap=()=>{const r:Record<string,number>={};for(const name of ['summary','judgment','tasks']){const el=document.querySelector(`[data-region="${name}"]`);if(!el)return null;const b=el.getBoundingClientRect();r[name]=b.top;r[name+'Height']=b.height;}return r;};
 new MutationObserver(()=>{if(document.querySelector('.provisional-result')){const b=snap();if(b)state.before=b;}else if(state.before&&!state.after&&document.querySelector('.result-stack:not(.provisional-result) .summary-text')?.textContent?.trim())state.after=snap();}).observe(document.body,{childList:true,subtree:true,characterData:true});
 });
 await p.getByLabel('요청 내용').fill('회의실 예약 조회 기능을 만들고 싶습니다.');await p.getByRole('button',{name:'요청 보내기'}).click();
 await expect(p.locator('.result-stack:not(.provisional-result)')).toBeVisible({timeout:60000});
 const state=await p.evaluate(()=>(window as any).__qaLayout);writeFileSync(join(process.env.ACC_UI_OUT!,`${browserName}-zero-layout.json`),JSON.stringify(state,null,2));
 await p.screenshot({path:join(process.env.ACC_UI_OUT!,`${browserName}-zero-layout.png`),fullPage:true});expect(state.before).not.toBeNull();expect(state.after).not.toBeNull();
 for(const key of ['summary','judgment','tasks','judgmentHeight'])expect.soft(state.after[key]-state.before[key],`${key} movement`).toBe(0);
 await p.getByRole('button',{name:'답변 복사',exact:true}).click();await expect(p.getByRole('button',{name:'복사됨',exact:true})).toBeVisible();await a.ctx.close();
});
