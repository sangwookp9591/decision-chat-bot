"""Probe the complete OpenAPI inventory and preserve concrete boundary responses."""
import json
import re
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

pytestmark = pytest.mark.asyncio(loop_scope='module')
EVIDENCE = Path(__file__).resolve().parents[1] / 'evidence'
HUGE = 2**80


def url_for(path):
    return re.sub(r'\{([^}]+)\}', lambda m: '1' if m[1] in {'version'} else 'qa-missing', path)


async def test_public_api_inventory_invalid_inputs(runtime):
    c = await runtime.login()
    rows=[]
    failures=[]
    expired_client=await runtime.login('all2')
    from jevtriage.auth.core import _token_hash
    await runtime.write("MATCH (s:Session {tenant_id:$tenant,token_hash:$hash}) SET s.expires_at=datetime()-duration('PT1S')",hash=_token_hash(expired_client.cookies['jev_session']))
    try:
        spec=(await c.get('/openapi.json')).json()
        for path, operations in spec['paths'].items():
            for method, operation in operations.items():
                if method not in {'get','post','put','patch','delete'}:
                    continue
                url=url_for(path)
                params={}
                for param in operation.get('parameters',[]):
                    if param['in']=='query' and param.get('required'):
                        params[param['name']]='qa-missing'
                if path.endswith('/stream'):
                    params['max_events']=1
                if path == '/api/auth/logout':
                    continue
                cases = [('malformed_json', {'content': b'{"qa":', 'headers':{'Content-Type':'application/json'}}),
                         ('missing_fields', {'json':{}}),
                         ('oversized_wrong_type', {'json':['QA'*11000]})] if method!='get' else [('invalid_query', {'params':{**params,'limit':'bad','days':'bad','depth':'bad'}})]
                if path.endswith('/stream'):
                    cases=[('invalid_cursor', {'headers':{'Last-Event-ID':'qa-invalid'}})]
                for name, kwargs in cases:
                    r=await c.request(method,url,headers={**c.headers,'Idempotency-Key':uuid4().hex,**kwargs.pop('headers',{})}, **kwargs)
                    rows.append({'method':method,'path':path,'case':name,'status':r.status_code,
                                 'error_body':r.text[:1200] if r.status_code>=400 else None})
                    if r.status_code>=500:
                        failures.append(rows[-1])
                if method!='get' and path!='/api/auth/login':
                    r=await c.request(method,url,json={},headers={'X-CSRF-Token':'','Idempotency-Key':uuid4().hex})
                    rows.append({'method':method,'path':path,'case':'no_csrf','status':r.status_code})
                    if r.status_code!=403:
                        failures.append(rows[-1])
                if path not in {'/api/auth/login','/api/health','/api/ready','/api/meta'}:
                    async with httpx.AsyncClient(base_url=str(c.base_url),timeout=30,cookies=expired_client.cookies) as expired:
                        r=await expired.request(method,url,params=params,json={} if method!='get' else None)
                    rows.append({'method':method,'path':path,'case':'expired_or_unknown_session','status':r.status_code})
                    if r.status_code>=500 or r.status_code<400:
                        failures.append(rows[-1])
        (EVIDENCE/'api-matrix.json').write_text(json.dumps({'openapi_paths':len(spec['paths']),
            'rows':rows,'failures':failures},ensure_ascii=False,indent=2))
        assert not failures, f'public API boundary failures: {failures}'
    finally:
        await c.aclose()
        await expired_client.aclose()


@pytest.mark.parametrize('path', [f'/api/policy/versions/{HUGE}',
    f'/api/graph/judgment?config_version={HUGE}',
    f'/api/learning/rules/qa-missing/versions/{HUGE}/validations'])
async def test_oversized_integer_never_causes_500(runtime,path):
    c=await runtime.login()
    try:
        r=await c.get(path)
        with (EVIDENCE/'oversized-integer.jsonl').open('a') as out:
            out.write(json.dumps({'path':path,'status':r.status_code,'body':r.text[:1000]})+'\n')
        assert r.status_code<500, f'oversized client integer returned {r.status_code}'
    finally:
        await c.aclose()


async def test_input_limits_and_foreign_tenant(runtime):
    c=await runtime.login()
    other='qa_c_foreign_'+uuid4().hex[:12]
    foreign_id='req_'+uuid4().hex
    from jevtriage.db.tx import write_tx
    async def seed(tx):
        await (await tx.run("CREATE (:Request {id:$id,tenant_id:$tenant,created_by:'foreign'})",
                            id=foreign_id,tenant=other)).consume()
    await write_tx(other,seed)
    try:
        r=await c.post('/api/requests',data={'text':'X'*20001},headers={'Idempotency-Key':uuid4().hex})
        assert 400<=r.status_code<500
        rows=[]
        for suffix in ('','/runs','/judgment','/progress','/corrections'):
            r=await c.get(f'/api/requests/{foreign_id}{suffix}')
            rows.append({'path':f'/api/requests/{foreign_id}{suffix}','status':r.status_code})
            assert r.status_code==404, (suffix,r.status_code)
        (EVIDENCE/'cross-tenant.json').write_text(json.dumps(rows,indent=2))
    finally:
        async def remove(tx):
            await (await tx.run('MATCH (n {tenant_id:$tenant}) DETACH DELETE n',tenant=other)).consume()
        await write_tx(other,remove)
        await c.aclose()


async def test_nested_review_changes_are_validated_before_service(runtime):
    c=await runtime.login()
    p=runtime.worker('qa-worker-invalid-review')
    rows=[]
    try:
        request=await runtime.submit(c,'QA-C malformed nested change payload')
        await runtime.terminal(request['request_id'],timeout=90)
        reviews=(await c.get('/api/reviews')).json()['reviews']
        review=next(v for v in reviews if v['request_id']==request['request_id'])
        command={'action':'approve_with_changes','request_id':request['request_id'],
            'input_revision':review['revision_id'],'run_id':request['run_id'],
            'draft_version':review['draft_version'],'review_version':review['review_version'],
            'reason':'QA-C malformed nested structure'}
        for changes in ({'classifications':['qa-invalid']},{'draft_tasks':['qa-invalid']},
                        {'draft_tasks':[{'draft_task_id':'draft-1','lead_org':['qa-invalid']}]},
                        {'classifications':{'ai_need':'qa-invalid'}}):
            r=await c.post('/api/reviews/'+review['id']+'/decision',
                           json={**command,'changes':changes},headers={'Idempotency-Key':uuid4().hex,'Connection':'close'})
            rows.append({'changes':changes,'status':r.status_code,'body':r.text[:1000]})
            (EVIDENCE/'nested-review-changes.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
        (EVIDENCE/'nested-review-changes.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
        assert all(400<=r['status']<500 for r in rows), f'unvalidated nested review payload: {rows}'
    finally:
        if p.poll() is None:
            p.terminate()
            import asyncio
            await asyncio.to_thread(p.wait,timeout=8)
        await c.aclose()
