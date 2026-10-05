const task=await taskSpace(4),p=task.page('p1');const fs=await import('node:fs/promises');const root='/Users/psw/Projects/decision-chat-bot/artifacts/review/completeness';const base='http://audit-e2e.localhost:7691';
await p.cdp('Page.addScriptToEvaluateOnNewDocument',{source:`window.auditErrors=[];addEventListener('error',e=>window.auditErrors.push(String(e.message)));addEventListener('unhandledrejection',e=>window.auditErrors.push(String(e.reason)));`});
const screens=[['request','/','requester'],['review','/review','reviewer'],['tasks','/tasks','team_member'],['observatory','/observatory','operator'],['map','/judgment-map','reviewer'],['learning','/learning','rule_admin'],['monitoring','/monitoring','operator'],['policy','/policy','policy_editor'],['evaluation','/evaluation','labeler']];
for(const [name,path,role] of screens){
 await p.goto(base+'/'); await p.fetch('/api/auth/login',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({email:role+'@t-audit-e2e-1005.dev',password:'dev-only-change-me'})});
 const times=[];
 for(let i=0;i<3;i++){const start=Date.now();await p.goto(base+path);await p.waitForFunction(()=>!!document.querySelector('main h1,main textarea')&&!document.querySelector('.login-page'),undefined,{timeout:15000});times.push(Date.now()-start);}
 const states=[];
 for(const width of [1440,960,375])for(const theme of ['light','dark']){
 await p.cdp('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});await p.cdp('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:theme}]});
 const metrics=await p.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,bg:getComputedStyle(document.body).backgroundColor,errors:window.auditErrors,alerts:[...document.querySelectorAll('[role=alert]')].map(x=>x.textContent),slow:performance.getEntriesByType('resource').filter(x=>x.duration>5000).map(x=>({url:x.name,duration:x.duration})),httpErrors:performance.getEntriesByType('resource').filter(x=>x.responseStatus>=400).map(x=>({url:x.name,status:x.responseStatus}))}));
 const file=`${name}-${width}-${theme}.png`;await p.screenshot({path:root+'/e2e/'+file});states.push({theme,...metrics,file});
 }
 await fs.appendFile(root+'/scratch/screen-metrics.jsonl',JSON.stringify({name,path,role,times,p50:[...times].sort((a,b)=>a-b)[1],states})+'\n'); console.log(name,times);
}
console.log(await p.snapshot());
