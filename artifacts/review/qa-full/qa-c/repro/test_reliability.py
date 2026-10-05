"""QA-C real-process concurrency, load, distributed SSE and masking controls."""
import asyncio
import json
import time
from pathlib import Path
from uuid import uuid4

import pytest
from test_shadow_masking import SAMPLES, TEXT, CaptureClient

from jevtriage.db.jobs import OwnershipLost, claim_or_takeover
from jevtriage.db.tx import read_tx
from jevtriage.jobs.worker import Worker
from jevtriage.judgment.service import execute_judgment
from jevtriage.ops.retention import RetentionConfig, cleanup

pytestmark=pytest.mark.asyncio(loop_scope='module')
EVIDENCE=Path(__file__).resolve().parents[1]/'evidence'


def record(name,value):
    (EVIDENCE/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str))


def percentiles(values):
    values=sorted(values)
    return {'samples':len(values),'p50_ms':round(values[int((len(values)-1)*.50)],2),
            'p95_ms':round(values[int((len(values)-1)*.95)],2)}


async def test_two_workers_claim_once(runtime):
    c=await runtime.login()
    try:
        r=await runtime.submit(c,'QA-C two workers claim')
        job=(await runtime.graph('MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id',run=r['run_id']))[0]['id']
        results=await asyncio.gather(*(claim_or_takeover(runtime.tenant,job,'qa-owner-'+str(i),10)
                                      for i in range(2)),return_exceptions=True)
        record('parallel-claim',{'results':[type(v).__name__ if isinstance(v,Exception) else v for v in results]})
        assert sum(isinstance(v,int) for v in results)==1
        assert sum(isinstance(v,OwnershipLost) for v in results)==1
        # Release the claimed probe explicitly; no background worker owns it.
        await runtime.write("MATCH (j:Job {tenant_id:$tenant,id:$id}) SET j.status='pending',j.lease_expires_at=null",id=job)
    finally:
        await c.aclose()


async def test_regular_external_masking_all_fields(runtime):
    c=await runtime.login()
    prior=(await runtime.graph("MATCH (p:ConfigVersion {tenant_id:$tenant,status:'active'}) RETURN p.config_json AS config"))[0]['config']
    policy=json.loads(prior)
    policy['rules']=[{'schema':'rule-v1','rule_id':'R-CONTEXT-QA','version':1,'effect':'context','target':'ai_need','scope':{'all':[]},'action':{'set':'혼합'},'context_text':TEXT}]
    await runtime.write("MATCH (p:ConfigVersion {tenant_id:$tenant,status:'active'}) SET p.config_json=$config",config=json.dumps(policy))
    try:
        r=await runtime.submit(c,TEXT)
        client=CaptureClient()
        async def handler(ctx):
            return await execute_judgment(ctx,client=client)
        w=Worker(handlers={'judgment':handler},tenants=[runtime.tenant])
        job=(await runtime.graph('MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id',run=r['run_id']))[0]['id']
        await w.process_job(runtime.tenant,job)
        assert client.payloads
        leaks={key:sum(value in json.dumps(p,ensure_ascii=False) for p in client.payloads) for key,value in SAMPLES.items()}
        record('regular-masking',{'calls':len(client.payloads),'leaked_sample_counts':leaks,
                                  'payloads':client.payloads})
        assert not any(leaks.values())
    finally:
        await runtime.write("MATCH (p:ConfigVersion {tenant_id:$tenant,status:'active'}) SET p.config_json=$config",config=prior)
        await c.aclose()


async def test_simultaneous_changed_approvals(runtime):
    c=await runtime.login()
    c2=await runtime.login('all2')
    p=runtime.worker('qa-worker-review')
    try:
        r=await runtime.submit(c,'QA-C concurrent corrected approval')
        state=await runtime.terminal(r['request_id'])
        assert state['status']=='judgment_saved'
        reviews=(await c.get('/api/reviews')).json()['reviews']
        v=next(v for v in reviews if v['request_id']==r['request_id'])
        command={'action':'approve_with_changes','request_id':r['request_id'],
                 'input_revision':v['revision_id'],'run_id':r['run_id'],
                 'draft_version':v['draft_version'],'review_version':v['review_version'],
                 'reason':'QA concurrency check','changes':{'classifications':{'urgency':'긴급'}}}
        keys=[uuid4().hex,uuid4().hex]
        clients=[c,c2]
        results=await asyncio.gather(*(client.post('/api/reviews/'+v['id']+'/decision',json=command,
                                      headers={'Idempotency-Key':key}) for client,key in zip(clients,keys)))
        winner=next((i for i,r in enumerate(results) if r.status_code==200),None)
        retry=(await clients[winner].post('/api/reviews/'+v['id']+'/decision',json=command,headers={'Idempotency-Key':keys[winner]})) if winner is not None else None
        counts=await runtime.graph(
            "MATCH (q:Request {tenant_id:$tenant,id:$id}) "
            "OPTIONAL MATCH (a:Assignment {tenant_id:$tenant,request_id:q.id}) "
            "OPTIONAL MATCH (t:Task {tenant_id:$tenant,request_id:q.id}) "
            "RETURN count(DISTINCT a) AS assignments,count(DISTINCT t) AS tasks,"
            "count(DISTINCT t.draft_task_id) AS distinct_tasks",id=r['request_id'])
        record('changed-approval-race',{'statuses':[r.status_code for r in results],
                                       'bodies':[r.json() for r in results],'counts':counts,'winner':winner,'retry_status':retry.status_code if retry else None})
        assert sorted(r.status_code for r in results)==[200,409]
        assert retry is not None and retry.status_code==200
        assert counts[0]['assignments']==1 and counts[0]['tasks']==counts[0]['distinct_tasks']
    finally:
        if p.poll() is None:
            p.terminate()
            await asyncio.to_thread(p.wait,timeout=8)
        await c.aclose()
        await c2.aclose()


async def test_load_20_intakes_1000_reviews(runtime):
    c=await runtime.login()
    prefix='load_'+uuid4().hex[:8]
    await runtime.write(
        "UNWIND range(1,1000) AS i "
        "CREATE (q:Request {tenant_id:$tenant,id:$prefix+'_q_'+toString(i),created_by:$author,"
        "org_ids:[$tenant+'-business'],shared_org_ids:[],title:'QA seeded review',status:'review_pending',"
        "created_at:datetime(),active_run_id:$prefix+'_run_'+toString(i),latest_revision_id:$prefix+'_rev_'+toString(i)}) "
        "CREATE (v:Review {tenant_id:$tenant,id:$prefix+'_v_'+toString(i),request_id:q.id,"
        "run_id:q.active_run_id,revision_id:q.latest_revision_id,status:'pending',draft_version:1,"
        "review_version:1,reasons:'[]',created_at:datetime(),required_reviewer_org:$tenant+'-business'})",
        prefix=prefix,author='all_'+runtime.tenant)
    p=runtime.worker('qa-worker-load')
    try:
        async def submit(i):
            t=time.perf_counter()
            r=await runtime.submit(c,f'QA-C load request {i}')
            return r,(time.perf_counter()-t)*1000
        submitted=await asyncio.gather(*(submit(i) for i in range(20)))
        states=await asyncio.gather(*(runtime.terminal(r['request_id'],timeout=90) for r,_ in submitted))
        samples={'intake':[ms for _,ms in submitted],'list':[],'detail':[],'sse':[]}
        statuses=[]
        for _ in range(30):
            for name,url in [('list','/api/reviews'),('detail','/api/reviews/'+prefix+'_v_1')]:
                t=time.perf_counter(); response=await c.get(url)
                samples[name].append((time.perf_counter()-t)*1000)
                statuses.append(response.status_code)
            t=time.perf_counter()
            async with c.stream('GET','/api/events/stream?after=0&max_events=1') as response:
                statuses.append(response.status_code)
                async for line in response.aiter_lines():
                    if line.startswith('id: '):
                        samples['sse'].append((time.perf_counter()-t)*1000)
                        break
        record('small-load',{'tenant':runtime.tenant,'seeded_reviews':1000,'concurrent_intakes':20,
                            'mode':'mock deterministic E2E fixture','stats':{k:percentiles(v) for k,v in samples.items()},
                            'response_statuses':statuses,'error_rate':sum(s>=400 for s in statuses)/len(statuses),
                            'run_states':states,'raw_latency_ms':samples})
        assert all(s==200 for s in statuses)
        assert all(s['status']=='judgment_saved' for s in states)
    finally:
        if p.poll() is None:
            p.terminate(); await asyncio.to_thread(p.wait,timeout=8)
        await runtime.write('MATCH (n {tenant_id:$tenant}) WHERE n.id STARTS WITH $prefix DETACH DELETE n',prefix=prefix)
        await c.aclose()


async def test_cancel_completion_race_20_times(runtime):
    from jevtriage.auth.core import Principal
    from jevtriage.jobs.cancel import cancel_run
    from tests.integration.test_cancel_run import setup_run, states
    outcomes=[]
    author=Principal(runtime.tenant,'author',(),frozenset({'requester'}),True)
    for i in range(20):
        request,run,job=await setup_run(runtime.tenant)
        entered,release=asyncio.Event(),asyncio.Event()
        async def handler(ctx, entered=entered, release=release):
            entered.set()
            await release.wait()
        w=Worker(handlers={'judgment':handler},tenants=[runtime.tenant])
        work=asyncio.create_task(w.process_job(runtime.tenant,job))
        await asyncio.wait_for(entered.wait(),10)
        release.set()
        await asyncio.gather(work,cancel_run(author,request,run))
        value=await states(runtime.tenant,request,run,job)
        outcomes.append(value)
        assert (value['run'],value['job']) in {('cancelled','cancelled'),('judgment_saved','completed')}
    record('cancel-race',{'samples':20,'outcomes':outcomes})


async def test_two_api_sse_resume_and_redis_restart(runtime):
    import shutil

    from redis.asyncio import Redis
    from redis.exceptions import RedisError

    from jevtriage.db.events import append_event
    c=await runtime.login(port=11491)
    c2=await runtime.login(port=11492)
    results=[]
    rows=await runtime.graph('MATCH (c:EventCounter {tenant_id:$tenant}) RETURN c.seq AS seq')
    cursor=rows[0]['seq'] if rows else 0
    async def receive(after):
        async with c2.stream('GET','/api/events/stream?max_events=1',headers={'Last-Event-ID':str(after)}) as s:
            assert s.status_code==200
            lines=[]
            async for line in s.aiter_lines():
                lines.append(line)
                if line.startswith('id: '):
                    return int(line[4:]),lines
        raise AssertionError('SSE did not return an event')
    try:
        for phase in ('redis_up','redis_down','redis_recovered'):
            if phase=='redis_down':
                runtime.procs['redis'].terminate()
                await asyncio.to_thread(runtime.procs['redis'].wait,timeout=8)
            if phase=='redis_recovered':
                runtime.start('redis-restarted',[shutil.which('redis-server'),'--port','11493','--save','','--appendonly','no'])
                probe=Redis.from_url('redis://127.0.0.1:11493/15')
                for _ in range(100):
                    try:
                        if await probe.ping():
                            break
                    except (RedisError, OSError):
                        await asyncio.sleep(.05)
                await probe.aclose()
            reader=asyncio.create_task(receive(cursor))
            await asyncio.sleep(.3)
            start=time.perf_counter()
            # First write uses API instance A; remaining phases use the durable business event boundary.
            if phase=='redis_up':
                r=await runtime.submit(c,'QA-C API A -> API B event')
                rows=await runtime.graph('MATCH (e:Event {tenant_id:$tenant,request_id:$id}) RETURN e.seq AS seq ORDER BY e.seq',id=r['request_id'])
                expected=rows[0]['seq']
            else:
                e=await append_event(runtime.tenant,'policy.published',{'version':1})
                expected=e['seq']
            seq,lines=await asyncio.wait_for(reader,12)
            results.append({'phase':phase,'previous_cursor':cursor,'received_seq':seq,
                            'expected_seq':expected,'latency_ms':round((time.perf_counter()-start)*1000,2),'lines':lines})
            assert seq==expected and seq>cursor
            cursor=seq
        record('two-api-redis-recovery',{'results':results,'duplicate_seq_count':len(results)-len({x['received_seq'] for x in results})})
    finally:
        await c.aclose(); await c2.aclose()


async def test_retention_dry_run_and_execution_preserve_business(runtime,tmp_path):
    from jevtriage.db.events import append_event
    await append_event(runtime.tenant,'policy.published',{'version':1})
    await runtime.write("MATCH (n {tenant_id:$tenant}) WHERE any(label IN labels(n) WHERE label IN ['Request','InputRevision','Run','Judgment','Review','Assignment','Task','Audit']) SET n.created_at=datetime()-duration('P1000D')")
    await runtime.write("MATCH (e:Event {tenant_id:$tenant}) SET e.created_at=datetime()-duration('P100D')")
    async def counts(tx):
        rows=[]
        for label in ('Request','InputRevision','Run','Judgment','Review','Assignment','Task','Audit'):
            r=await (await tx.run(f'MATCH (n:{label} {{tenant_id:$tenant}}) RETURN count(n) AS n',tenant=runtime.tenant)).single()
            rows.append((label,r['n']))
        return dict(rows)
    before=await read_tx(runtime.tenant,counts)
    dry=await cleanup(data_dir=tmp_path,tenant_id=runtime.tenant,config=RetentionConfig(),dry_run=True)
    after_dry=await read_tx(runtime.tenant,counts)
    actual=await cleanup(data_dir=tmp_path,tenant_id=runtime.tenant,config=RetentionConfig())
    after=await read_tx(runtime.tenant,counts)
    record('retention',{'before':before,'after_dry_run':after_dry,'after_execute':after,'dry_run':dry,'execute':actual})
    assert before==after_dry==after
    assert dry['deleted']==actual['deleted'] and dry['deleted']['events']>0


