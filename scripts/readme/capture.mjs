// Run via ego-browser nodejs < scripts/readme/capture.mjs (no separate browser).
const fs = await import('node:fs/promises');
const cfg = JSON.parse(await fs.readFile('/tmp/jev-readme-session.json','utf8'));
const seed = JSON.parse(await fs.readFile(cfg.out+'/seed.json','utf8'));
const task = await taskSpace(cfg.captureSpace || 'README 화면 촬영');
console.log('README_SPACE='+task.spaceId);
const p = task.page('p1'), base='http://127.0.0.1:7791';
const stage=cfg.captureStage || 'all';
cfg.captureSpace=task.spaceId; await fs.writeFile('/tmp/jev-readme-session.json',JSON.stringify(cfg));
async function size(mobile=false) {
  await p.cdp('Emulation.setDeviceMetricsOverride',{width:mobile?375:1440,height:900,deviceScaleFactor:2,mobile});
}
async function theme(value) { await p.cdp('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value}]}); }
async function clean() {
  // Capture-only privacy treatment: hide account names and technical identifiers.
  // No product copy, judgments, statuses, or API responses are changed.
  await p.evaluate(()=>{
    if(!document.querySelector('#readme-privacy')) { const s=document.createElement('style'); s.id='readme-privacy'; s.textContent='.sidebar-user strong,.topbar-account>span:first-child,.request-id{visibility:hidden!important}'; document.head.append(s); }
    for(const e of document.querySelectorAll('code,small,strong,span')) {
      if(e.childElementCount===0 && /^(?:usr_|req_|task_|t-readme-|run_|rev_|draft_|cand_|corr_)[\w….-]+$/.test(e.textContent.trim())) e.style.visibility='hidden';
    }
    const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT); let node; while((node=walker.nextNode())) { if(!['SCRIPT','STYLE'].includes(node.parentElement?.tagName)) node.textContent=node.textContent.replace(/t-readme-[a-z0-9-]+/g,'시연 조직').replace(/(?:usr|req|rev|run|cand|corr|step|worker)_[a-zA-Z0-9_….-]+/g,'…'); }
    for(const video of document.querySelectorAll('video')) { if(video.readyState>=2) video.pause(); }
  });
}
async function snap(name) { await clean(); await fs.writeFile(cfg.out+'/'+name+'.png',Buffer.from((await p.cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64')); console.log('CAPTURE '+name); }
async function login(role) {
  const r=await p.fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:`${role}@${cfg.tenant}.dev`,password:'dev-only-change-me'})});
  if(r.status!==200) throw Error('Login '+role+' '+r.status);
}
async function go(route,selector) { await p.goto(base+route); if(selector) await p.waitForSelector(selector,{state:'visible',timeout:20000}); await p.evaluate(()=>document.fonts.ready.then(()=>true)); }
await size(); await theme('light'); await p.goto(base);
if(stage==='all'||stage==='chat') {
  await login('requester'); await go('/','textarea');
  await p.waitForSelector('.request-row',{state:'visible'});
  await snap('hero');
  await p.fill('textarea','회의실 예약 현황을 한눈에 확인하는 대시보드를 만들고 싶습니다. 부서별 예약과 이용 시간을 집계하고 중복 예약을 알려 주세요. 현업이 요구사항과 수용 기준을 정하고 IT팀이 데이터 연결과 화면 개발을 담당합니다. 가상 시연 자료이며 민감 정보는 없습니다.');
  await p.evaluate(()=>document.querySelector('button[aria-label="요청 보내기"]').click());
  let provisional=false, final=false, typing=false;
  const deadline=Date.now()+90000;
  while(Date.now()<deadline) {
    const state=await p.evaluate(()=>({typing:!!document.querySelector('.typing-bubble'),provisional:!!document.querySelector('.provisional-badge'),final:!!document.querySelector('[data-region=summary] .environment-badge.mode-live')}));
    if(state.typing&&!typing) { await snap('progress-typing'); typing=true; }
    if(state.provisional&&!provisional) { await snap('progress-provisional'); provisional=true; }
    if(state.final) { final=true; break; }
  }
  if(!provisional||!final) throw Error('Progressive capture missed a required state');
  await p.evaluate(()=>document.querySelector('.result-summary')?.scrollIntoView({block:'start'}));
  await snap('judgment');
  cfg.requestId = new URL(await p.url()).searchParams.get('request_id');
  // URL stays on / in some builds; read the selected list item via persisted API.
  if(!cfg.requestId) {
    const r=await p.fetch('/api/requests');
    const body=typeof r.body==='string'?JSON.parse(r.body):r.body;
    cfg.requestId=(body.requests||body.items||body)[0].id;
  }
  await fs.writeFile('/tmp/jev-readme-session.json',JSON.stringify(cfg));
  console.log('CHAT READY');
}
if(stage==='all'||stage==='panels') {
  if(!cfg.requestId) throw Error('Capture chat first');
  await login('reviewer'); await go('/review?request_id='+cfg.requestId,'[aria-label="AI 필요성 수정"]');
  await snap('review');
  await size(true); await snap('mobile-review'); await size();
  await login('team_member'); await go('/tasks','.task-list > button'); await snap('tasks');
  await login('operator'); await go('/judgment-map?request_id='+cfg.requestId,'.jm-node:not(.is-group)');
  await p.click('text="크게 보기"');
  const nodes=await p.evaluate(()=>[...document.querySelectorAll('.jm-node:not(.is-group)')].map(e=>e.getAttribute('aria-label')));
  if(nodes.at(-1)) await p.click('button[aria-label='+JSON.stringify(nodes.at(-1))+']');
  else await p.click('.jm-node:not(.is-group) >> nth=-1');
  await snap('map');
  await login('rule_admin'); await go('/learning?candidate_id='+seed.candidate,'h1'); await p.waitForFunction(()=>document.body.innerText.includes('ai_need')||document.body.innerText.includes('AI 필요성')); await snap('learning');
  await login('labeler'); await go('/evaluation','[role=radiogroup]'); await snap('evaluation');
  await login('operator'); await go('/monitoring','h1'); await p.waitForFunction(()=>!document.body.innerText.includes('불러오는 중')); await snap('monitoring');
  await login('policy_editor'); await go('/policy','fieldset'); await snap('policy');
  await login('requester'); await theme('dark'); await go('/?request_id='+cfg.requestId,'.result-brief'); await snap('dark');
  await theme('light'); await size(true); await snap('mobile-chat'); await size();
}
if(stage==='all' && !cfg.keepSpace) { await task.finish({keep:[]}); delete cfg.captureSpace; await fs.writeFile('/tmp/jev-readme-session.json',JSON.stringify(cfg)); }
