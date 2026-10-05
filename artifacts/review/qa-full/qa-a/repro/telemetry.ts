import {test,type Page,type Browser} from '../../../../../frontend/node_modules/@playwright/test';
import {actor as baseActor} from '../../../../../frontend/e2e/acceptance/helpers';
import {appendFileSync} from 'node:fs';
import {join} from 'node:path';
export function watch(page:Page){
 const log=(data:object)=>appendFileSync(join(process.env.ACC_UI_OUT!,'telemetry.jsonl'),JSON.stringify({at:new Date().toISOString(),test:test.info().title,browser:test.info().project.name,...data})+'\n');
 const starts=new Map<any,number>();
 page.on('pageerror',error=>log({kind:'pageerror',error:error.message}));
 page.on('console',message=>{if(message.type()==='error')log({kind:'console',error:message.text()})});
 page.on('request',r=>starts.set(r,Date.now()));
 page.on('requestfailed',r=>log({kind:'requestfailed',url:r.url(),error:r.failure()?.errorText}));
 page.on('response',r=>{if(r.status()>=400)log({kind:'http',url:r.url(),status:r.status()})});
 page.on('requestfinished',r=>{const duration=Date.now()-(starts.get(r)||Date.now());starts.delete(r);if(duration>=5000&&!r.url().includes('/events'))log({kind:'slow-request',url:r.url(),duration_ms:duration})});
}
export async function actor(browser:Browser,base:string,role:string){const a=await baseActor(browser,base,role);watch(a.page);a.ctx.on('page',watch);return a}
