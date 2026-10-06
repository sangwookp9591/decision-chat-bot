import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
const require=createRequire(new URL('../../frontend/package.json',import.meta.url));
const {chromium,request,expect}=require('@playwright/test');
const OUT=process.env.DEMO_OUT,T=process.env.DEMO_TENANT,BASE='http://127.0.0.1:7591';
const password='dev-only-change-me';
const scenes=[],ids=[],notes=[],timing={},consoleErrors=[];
let primary,chat,candidate;
const demoText='사내 회의실 예약 현황을 부서별로 조회하고 예약 가능 시간을 확인하는 화면이 필요합니다. 데이터 존재 여부와 접근 권한, 품질을 확인해야 합니다. 현업이 수용 기준과 업무 범위를 정하고 IT팀이 데이터 연결과 화면 개발을 담당합니다. 가상 시연 자료이며 민감 정보는 없습니다.';
fs.writeFileSync(path.join(OUT,'회의실-요구사항.md'),'# 회의실 예약 현황 자동 집계\n\n'+demoText+'\n\n## 업무 순서\n1. 예약 자료 수집\n2. 중복 예약 확인\n3. 현업 확인 후 주간 보고서 작성\n');
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function login(api,role,tenant=T){const r=await api.post('/api/auth/login',{data:{email:`${role}@${tenant}.dev`,password}});if(!r.ok())throw Error('로그인 실패 '+role+' '+r.status());}
async function apiAs(role){const api=await request.newContext({baseURL:BASE});await login(api,role);return api;}
async function call(api,method,url,data){const csrf=(await api.storageState()).cookies.find(c=>c.name==='ildongi_csrf')?.value;const r=await api.fetch(url,{method,headers:{'X-CSRF-Token':csrf||'','Idempotency-Key':crypto.randomUUID()},...(data?{data}:{})});if(!r.ok())throw Error(`${method} ${url}: ${r.status()} ${(await r.text()).slice(0,250)}`);return r.json();}
async function judged(api,id){for(let i=0;i<100;i++){const r=await api.get(`/api/requests/${id}/judgment`);if(r.ok()){const j=await r.json();if(j.mode!=='live')throw Error('LIVE가 아닌 판단');return j;}await wait(600);}throw Error('실제 Decision AI 최종 결과 대기 60초 초과');}
async function submitAPI(api,text){const csrf=(await api.storageState()).cookies.find(c=>c.name==='ildongi_csrf')?.value;const r=await api.post('/api/requests',{headers:{'X-CSRF-Token':csrf||'','Idempotency-Key':crypto.randomUUID()},multipart:{text}});if(!r.ok())throw Error('요청 접수 '+r.status());const a=await r.json();ids.push(a.request_id);await judged(api,a.request_id);return a.request_id;}
async function caption(p,text){await p.evaluate(text=>{let el=document.getElementById('demo-caption');if(!el){el=document.createElement('div');el.id='demo-caption';document.body.appendChild(el);}el.textContent=text;el.style.cssText='position:fixed;top:0;left:0;right:0;z-index:2147483647;background:rgba(12,23,42,.93);color:#fff;padding:12px 28px;font:600 19px/1.6 "Apple SD Gothic Neo",sans-serif;border-bottom:3px solid #65d6b6;pointer-events:none';document.documentElement.style.scrollPaddingTop='100px';document.body.style.paddingTop='64px';},text);}
async function card(p,title,sub){await p.setContent(`<html lang="ko"><body style="margin:0;background:#0b162b;color:#f5f8ff;font-family:'Apple SD Gothic Neo',sans-serif;display:flex;align-items:center;justify-content:center;height:900px"><div style="width:1100px"><p style="color:#65d6b6;font-size:23px;letter-spacing:5px">AI TRIAGE · LIVE WALKTHROUGH</p><h1 style="font-size:52px;line-height:1.4">${title}</h1><p style="font-size:26px;line-height:1.8;color:#b9c9e2">${sub}</p></div></body></html>`);}
async function click(p,loc){await loc.scrollIntoViewIfNeeded();await wait(850);await loc.click();await wait(950);}
async function go(p,url,text){await p.goto(url);await p.waitForLoadState('domcontentloaded');await caption(p,text);await wait(1200);}
async function scroll(p,loc){await loc.scrollIntoViewIfNeeded();await wait(2200);}
// Prepare real, isolated correction history before the camera starts.
const rq=await apiAs('requester'),rev=await apiAs('reviewer'),admin=await apiAs('rule_admin');
for(let i=0;i<3;i++){
 const id=await submitAPI(rq,demoText+` 가상 시연 반복 사례 ${i+1}.`);
 const reviews=await call(rev,'GET','/api/reviews?status=pending');
 const row=reviews.reviews.find(r=>r.request_id===id);if(!row)throw Error('검토 대기 없음');
 const d=await call(rev,'GET',`/api/reviews/${row.id}`);
 await call(rev,'POST',`/api/reviews/${row.id}/decision`,{action:'approve_with_changes',request_id:id,input_revision:row.revision_id,run_id:row.run_id,draft_version:row.draft_version,review_version:row.review_version,changes:{classifications:{ai_need:d.final_classifications.ai_need==='필요'?'불필요':'필요'}},reason:'가상 시연: 원문과 같은 방향의 판단 수정 사례를 검토합니다.'});
 console.log('PREPARED_CORRECTION',i+1);
}
await call(admin,'POST','/api/learning/candidates/generate');
candidate=(await call(admin,'GET','/api/learning/candidates')).candidates.find(c=>c.field==='ai_need');
if(!candidate)throw Error('수정 이력 후보 없음');
const reason='가상 시연: 제한된 표본임을 확인하고 전용 회사 범위의 초안으로만 보존합니다.';
const decision=await call(admin,'POST',`/api/learning/candidates/${candidate.id}/decision`,{action:'approve_with_scope_change',scope:{all:[{requester_org:`${T}-ai`}]},reason,acknowledge_insufficient:true});
await call(admin,'POST','/api/learning/rules/R-DEMO-01/versions',{decision_id:decision.decision_id,body:{},reason,acknowledge_insufficient:true});
await rq.dispose();await rev.dispose();await admin.dispose();
const browser=await chromium.launch({headless:true});
const ctx=await browser.newContext({baseURL:BASE,viewport:{width:1440,height:900},deviceScaleFactor:1,reducedMotion:'no-preference',colorScheme:'light',recordVideo:{dir:path.join(OUT,'raw'),size:{width:1440,height:900}}});
ctx.setDefaultTimeout(15000);
const p=await ctx.newPage();
p.on('console',m=>{if(m.type()==='error')consoleErrors.push({type:'console',scene:scenes.length+1,text:m.text(),location:m.location()});});
p.on('pageerror',e=>consoleErrors.push({type:'pageerror',scene:scenes.length+1,text:e.message}));
const cameraStart=Date.now();
async function snap(name){await p.screenshot({path:path.join(OUT,name+'.png')});}
async function scene(n,title,role,seconds,fn){
 if(role)await login(ctx.request,role);
 const start=Date.now(),info={n,title,start:(start-cameraStart)/1000,status:'completed',limitations:[]};
 console.log('SCENE',n,title);
 try{await fn(p,ctx,info);}catch(e){info.status='partial';info.error=e.message.split('\n')[0];console.log('PARTIAL',n,info.error);await caption(p,`${n} · 시연 한계: ${info.error.slice(0,90)}`);}
 if(Date.now()-start<seconds*1000)await wait(seconds*1000-(Date.now()-start));
 await snap(`scene-${String(n).padStart(2,'0')}`);info.duration=(Date.now()-start)/1000;scenes.push(info);
 fs.writeFileSync(path.join(OUT,'raw/manifest.json'),JSON.stringify({tenant:T,ids,timing,notes,scenes,consoleErrors},null,2));
}
try{
await scene(1,'로그인',null,8,async()=>{
 await go(p,'/','01 · 일동이 — 업무 요청부터 검토·실행까지, 역할에 맞게 로그인합니다.');
 await p.getByLabel('이메일',{exact:true}).fill(`requester@${T}.dev`);await p.getByLabel('암호',{exact:true}).fill(password);await snap('scene-01-login');
 await click(p,p.getByRole('button',{name:'로그인',exact:true}));await p.getByLabel('요청 내용',{exact:true}).waitFor();
});
await scene(2,'일동이 인사·예시에서 요청 전송',null,0,async()=>{
 await caption(p,'02 · 빈 대화의 인사와 예시 칩에서 시작합니다. 요청을 보내면 입력창이 아래로 이동합니다.');
 await click(p,p.getByRole('group',{name:'예시 요청'}).getByRole('button').first());await snap('scene-02-greeting');
 await p.getByLabel('요청 내용',{exact:true}).fill(demoText);await wait(1800);
 await p.evaluate(()=>{window.demoTiming={start:Date.now()};const ob=new MutationObserver(()=>{for(const [key,selector]of [['typing','.typing-bubble'],['preliminary','.provisional-badge'],['final','[data-region=summary] .environment-badge.mode-live']])if(!window.demoTiming[key]&&document.querySelector(selector))window.demoTiming[key]=Date.now()-window.demoTiming.start;});ob.observe(document.body,{subtree:true,childList:true});});
 const response=p.waitForResponse(r=>r.url().endsWith('/api/requests')&&r.request().method()==='POST');
 await p.getByRole('button',{name:'요청 보내기',exact:true}).click();primary=(await(await response).json()).request_id;ids.push(primary);
 await p.locator('.typing-bubble').waitFor({timeout:5000});await snap('scene-02-typing');
});
await scene(3,'잠정 판단·최종 요약·자세히 보기',null,13,async()=>{
 await caption(p,'03 · 타이핑 점에서 잠정 판단으로, 실제 LIVE 판단이 끝나면 최종 요약 카드가 나타납니다.');
 await p.locator('.provisional-badge').first().waitFor({timeout:70000});await snap('scene-03-provisional');
 await p.locator('[data-region=summary] .environment-badge.mode-live').waitFor({timeout:70000});Object.assign(timing,await p.evaluate(()=>window.demoTiming));
 await p.locator('.result-brief .result-summary').first().evaluate(el=>el.scrollIntoView({block:'start',behavior:'smooth'}));await wait(2400);await snap('scene-03-summary');await click(p,p.getByRole('button',{name:'자세히 보기',exact:true}));await p.getByRole('dialog',{name:'판단 상세'}).waitFor();await wait(1800);
 await p.getByRole('dialog',{name:'판단 상세'}).getByRole('button',{name:'닫기',exact:true}).click();
});
await scene(4,'분석 정지·취소됨·다시 분석',null,15,async()=>{
 await click(p,p.locator('.request-list .new-chat'));
 await caption(p,'04 · 다른 요청을 보낸 뒤 정지합니다. 취소된 요청은 다시 분석할 수 있습니다.');
 await p.getByLabel('요청 내용',{exact:true}).fill('가상 주간 회의실 이용 보고서를 자동 작성하고 싶습니다. 현업이 요구 기준을 확인하고 IT팀이 자료를 연결합니다.');
 const response=p.waitForResponse(r=>r.url().endsWith('/api/requests')&&r.request().method()==='POST');await p.getByRole('button',{name:'요청 보내기',exact:true}).click();chat=(await(await response).json()).request_id;ids.push(chat);
 await p.getByRole('button',{name:'분석 정지',exact:true}).click();await p.locator('.cancelled-notice').waitFor();await wait(2000);await snap('scene-04-cancelled');
 p.once('dialog',dialog=>dialog.accept());await click(p,p.getByRole('button',{name:'다시 분석',exact:true}));await p.locator('[data-region=summary] .environment-badge.mode-live').waitFor({timeout:70000});await p.locator('.result-brief .result-summary').first().evaluate(el=>el.scrollIntoView({block:'start',behavior:'smooth'}));await wait(1500);
});
await scene(5,'왼쪽 대화 목록·날짜·제목',null,7,async()=>{
 await caption(p,'05 · 왼쪽 대화 목록은 날짜별로 묶이고 요청 원문에서 가져온 제목으로 다시 찾습니다.');
 await p.locator('.request-list .list-group').first().waitFor();await click(p,p.locator('.request-list .request-row').filter({hasText:primary}));await p.locator('.result-brief').waitFor();
});
await scene(6,'검토 대기·원문·수정 승인','reviewer',15,async()=>{
 await go(p,`/review?request_id=${primary}`,'06 · 검토 대기 제목과 요청 원문을 읽고, AI 원안을 수정 승인합니다.');
 await p.getByLabel('AI 필요성 수정').waitFor();await snap('scene-06-original');
 const field=p.getByLabel('담당 조직 수정');await field.fill((await field.inputValue())==='현업'?'IT팀':'현업');
 await p.getByLabel('결정 사유',{exact:true}).fill('가상 시연: 원문을 검토하여 담당 조직의 책임을 확정했습니다.');
 await click(p,p.getByRole('button',{name:'수정 승인',exact:true}));await p.getByText('결정을 저장했습니다.',{exact:false}).waitFor();
});
await scene(7,'업무 배정·상태 전이','team_member',14,async()=>{
 await go(p,'/tasks','07 · 승인 후 배정된 업무와 선행 관계를 확인하고, 시작 가능한 업무를 진행으로 바꿉니다.');
 const buttons=p.locator('.task-list > button');await buttons.first().waitFor();let moved=false;
 for(let i=0;i<Math.min(await buttons.count(),12);i++){await click(p,buttons.nth(i));const b=p.getByRole('button',{name:'진행으로 변경',exact:true});if(await b.count()&&await b.isEnabled()){await click(p,b);await p.getByText('업무 상태를 갱신했습니다.').waitFor();moved=true;break;}await p.getByRole('dialog',{name:'업무 상세'}).getByRole('button',{name:'닫기',exact:true}).click();}
 if(!moved)throw Error('시작 가능한 업무 없음');
});
await scene(8,'실행 관찰·재생·Trace','operator',16,async()=>{
 await go(p,`/observatory?request_id=${primary}`,'08 · 실제 저장된 실행 흐름을 재생하고 단계별 Trace와 업무 관계를 살펴봅니다.');
 await p.getByLabel('재생 속도').selectOption('2');await click(p,p.getByRole('button',{name:'재생',exact:true}));await wait(2200);
 await click(p,p.getByRole('button',{name:'전체 결과',exact:true}));await click(p,p.locator('.obs-node').nth(2));await wait(1800);await snap('scene-08-trace');
 await p.getByRole('dialog',{name:'Trace 상세'}).getByRole('button',{name:'닫기',exact:true}).click();await click(p,p.getByRole('button',{name:'업무 Topology',exact:true}));
});
await scene(9,'판단 맵·경로 글로우·버전 탭','operator',18,async()=>{
 await go(p,`/judgment-map?request_id=${primary}`,'09 · 판단 맵의 다크 무대에서 노드를 고르면 연결된 근거와 업무 경로가 빛납니다.');
 await p.locator('.jm-node:not(.is-group)').first().waitFor();await click(p,p.getByRole('button',{name:'크게 보기',exact:true}));await click(p,p.locator('.jm-node:not(.is-group)').last());await wait(1700);await snap('scene-09-glow');
 await go(p,'/judgment-map?rule_id=R-DEMO-01','09 · 실제 수정 이력에서 만든 규칙 초안의 버전 탭으로 관계를 좁혀 봅니다.');
 await p.getByRole('tab',{name:/v1/}).waitFor();await click(p,p.getByRole('tab',{name:/v1/}));await click(p,p.locator('.jm-node:not(.is-group)').first());
});
await scene(10,'규칙 학습 후보','rule_admin',10,async()=>{
 await go(p,`/learning?candidate_id=${candidate.id}`,'10 · 실제 수정 승인 이력에서 모은 학습 후보와 근거를 봅니다. 초안은 운영에 게시하지 않았습니다.');
 await p.getByRole('heading',{name:/규칙 학습/}).first().waitFor();await wait(1600);await p.mouse.wheel(0,300);
});
await scene(11,'평가 라벨·칩·Enter·J','labeler',13,async()=>{
 await go(p,'/evaluation','11 · 정답 칩을 선택하고 Enter로 확정합니다. J를 누르면 다음 표본으로 이동합니다.');
 const groups=p.getByRole('radiogroup');await groups.first().waitFor();
 for(let i=0;i<await groups.count();i++){const group=groups.nth(i);if(!await group.locator('[aria-checked=true]').count())await group.getByRole('radio').first().click();}
 await click(p,groups.first().getByRole('radio').first());await p.keyboard.press('Enter');await p.getByText('라벨을 확정했습니다.',{exact:true}).waitFor();await snap('scene-11-confirmed');
 await expect(p.getByRole('button',{name:'다음 (J)',exact:true})).toBeEnabled();await p.keyboard.press('j');await wait(1500);await p.mouse.wheel(0,-1000);
});
await scene(12,'모니터링·숫자 애니메이션','operator',10,async()=>{
 await go(p,'/monitoring','12 · 접수·검토·배정과 지연 지표가 채워집니다. 숫자 애니메이션과 관측 표본을 함께 확인합니다.');await wait(2600);await snap('scene-12-counts');await p.mouse.wheel(0,420);
});
await scene(13,'정책 폼·검증','policy_editor',10,async()=>{
 await go(p,'/policy','13 · 정책 폼에서 기준을 확인하고 서버 검증을 실행합니다. 게시에는 별도의 사유가 필요합니다.');
 await p.getByRole('group',{name:'선택형 판단 최소 확신도',exact:true}).waitFor();await click(p,p.getByRole('button',{name:'서버 검증',exact:true}));await p.getByText('검증 통과',{exact:true}).waitFor();await p.mouse.wheel(0,-2000);
});
await scene(14,'시스템 다크 모드','requester',9,async()=>{
 await p.emulateMedia({colorScheme:'dark',reducedMotion:'no-preference'});await go(p,`/?request_id=${primary}`,'14 · 시스템의 다크 모드를 따라 대화·카드·목록이 함께 바뀝니다.');await p.locator('.result-brief').waitFor();
});
await scene(15,'요청에서 검토·실행·학습까지',null,7,async()=>{
 await card(p,'업무 요청이 업무가 되기까지','일동이와 대화 → 근거 기반 판단 → 사람의 검토<br>업무 배정과 실행 → 관찰과 규칙 학습<br><br>실제 LIVE 판단 · 새 디자인 · 분석 취소와 재시작');
});
}finally{await ctx.close();await browser.close();}
const raw=await p.video().path();
console.log('ENCODING');
execFileSync('ffmpeg',['-y','-loglevel','error','-i',raw,'-vf','fps=30,scale=1440:900','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-an','-movflags','+faststart',path.join(OUT,'walkthrough.mp4')]);
const probe=JSON.parse(execFileSync('ffprobe',['-v','error','-show_entries','format=duration,size:stream=codec_name,width,height,r_frame_rate','-of','json',path.join(OUT,'walkthrough.mp4')],{encoding:'utf8'}));
const timecode=s=>`${String(Math.floor(s/60)).padStart(2,'0')}:${String(Math.floor(s%60)).padStart(2,'0')}`;
fs.writeFileSync(path.join(OUT,'chapters.md'),'# 한국어 시연 챕터\n\n'+scenes.map(s=>`- ${timecode(s.start)} — ${s.n}. ${s.title}${s.status==='partial'?' (부분 실패)':''}`).join('\n')+'\n');
fs.writeFileSync(path.join(OUT,'manifest.json'),JSON.stringify({tenant:T,ids,timing,notes,scenes,consoleErrors,probe},null,2));
const pngs=fs.readdirSync(OUT).filter(f=>f.endsWith('.png')).sort();
fs.writeFileSync(path.join(OUT,'README.md'),`# 일동이 현재 제품 흐름 시연\n\n- 실행: \`bash scripts/demo/record.sh\`\n- 기준 commit: ${process.env.DEMO_COMMIT}\n- 전용 API 10291 · Vite 7591 · tenant \`${T}\` · tenant 제한 worker\n- AI_MODE=live. .env는 Settings가 읽으며 키는 출력하거나 녹화하지 않습니다.\n- 1440×900 · 30 fps · H.264 · 한국어 자막 · reduced-motion 해제. 시스템 다크 모드는 장면 14에서 켭니다.\n- 로그인부터 마무리까지 하나의 연속 브라우저 녹화입니다. 실제 응답 및 애니메이션을 조작하지 않습니다.\n- 녹화 전 실제 LIVE 요청 3건을 수정 승인하고 학습 후보와 규칙 초안을 공개 API로 생성했습니다. 운영 게시하지 않았습니다.\n- 백엔드 판단 결과와 제품 코드는 변경하지 않았습니다.\n- 콘솔 오류: ${consoleErrors.length}건 · 부분 실패: ${scenes.filter(s=>s.status==='partial').length}장면\n- 재현 시험: 변경 전 REC-2 계약 시험 2건 실패(기존 포트·13개 장면), 변경 후 통과.\n\n## 영상\n\n[walkthrough.mp4](walkthrough.mp4) · ${(Number(probe.format.duration)).toFixed(2)}초 · ${(Number(probe.format.size)/1048576).toFixed(2)} MiB\n\n[타임코드](chapters.md) · [검증 manifest](manifest.json)\n\n## 장면 PNG 목록\n\n${pngs.map(f=>`- [${f}](${f})`).join('\n')}\n\n## 한계 및 오류\n\n${scenes.filter(s=>s.error).map(s=>`- 장면 ${s.n}: ${s.error}`).join('\n')||'장면 실행 오류 없음.'}\n\n${consoleErrors.map(e=>`- ${e.type}, 장면 ${e.scene}: ${e.text}`).join('\n')||'브라우저 console error 및 pageerror 없음.'}\n\n## 콘솔 응답 해석\n\n로그인 전 인증 확인 401, 저장 전 판단 조회 404, 미게시 초안의 효과 조회 404는 예상된 HTTP 응답이지만 브라우저 콘솔에 오류로 찍힙니다. 각 위치는 manifest의 consoleErrors에 보존합니다. React 경고와 pageerror가 있으면 별도 제품 결함으로 다룹니다.\n\n## 실측 표시 시간\n\n${JSON.stringify(timing)}\n\n클릭 직전 관찰자 설치부터 해당 DOM 최초 표시까지의 밀리초이며 서버 지연과 다릅니다.\n`);
console.log('FINISHED',JSON.stringify(probe),'PARTIAL',scenes.filter(s=>s.status==='partial').map(s=>s.n),'CONSOLE_ERRORS',consoleErrors.length);
if(scenes.some(s=>s.status==='partial'))process.exitCode=1;
