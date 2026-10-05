"""Real dedicated QA API processes and tenant fixtures; never touch shared services."""
import asyncio
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import httpx
import pytest_asyncio

ROOT = Path(__file__).resolve().parents[5]
EVIDENCE = Path(__file__).resolve().parents[1] / 'evidence'


@pytest_asyncio.fixture(scope='module', loop_scope='module')
async def runtime():
    from jevtriage.auth.core import hash_password
    from jevtriage.db.schema import apply_schema
    from jevtriage.db.tx import read_tx, write_tx
    from jevtriage.policy.service import bootstrap_policy
    assert ':7688' in os.environ.get('NEO4J_URI', ''), 'Dedicated QA Neo4j required'
    tenant = 'qa_c_' + uuid4().hex[:12]
    await apply_schema()
    await bootstrap_policy(tenant)
    roles = ['requester', 'reviewer', 'operator', 'policy_editor', 'rule_admin', 'labeler', 'team_member']
    async def seed(tx):
        await (await tx.run(
            "CREATE (t:Tenant {id:$tenant,tenant_id:$tenant}) "
            "WITH t UNWIND $orgs AS org CREATE (o:Org {id:org,tenant_id:$tenant,name:org}) CREATE (t)-[:HAS_ORG]->(o)",
            tenant=tenant, orgs=[tenant+'-'+x for x in ('business', 'it', 'ai')])).consume()
        await (await tx.run(
            "UNWIND ['all','all2'] AS user "
            "CREATE (u:User {id:user+'_'+$tenant,tenant_id:$tenant,email:user+'@'+$tenant+'.invalid',"
            "password_hash:$hash,disabled:false,can_read_source:true}) "
            "WITH u MATCH (o:Org {tenant_id:$tenant}) WITH u,o UNWIND $roles AS role "
            "CREATE (u)-[:MEMBER_OF {role:role}]->(o)",
            tenant=tenant, hash=hash_password('qa-only-password'), roles=roles)).consume()
    await write_tx(tenant, seed)

    class Harness:
        async def graph(self, query, **params):
            async def op(tx):
                return await (await tx.run(query, tenant=tenant, **params)).data()
            return await read_tx(tenant, op)

        async def write(self, query, **params):
            async def op(tx):
                return await (await tx.run(query, tenant=tenant, **params)).data()
            return await write_tx(tenant, op)

        async def login(self, user='all', port=11491):
            c = httpx.AsyncClient(base_url=f'http://127.0.0.1:{port}', timeout=30)
            r = await c.post('/api/auth/login', json={'email':user+'@'+tenant+'.invalid',
                                                    'password':'qa-only-password'})
            assert r.status_code == 200, r.status_code
            c.headers['X-CSRF-Token'] = c.cookies['jev_csrf']
            return c

        async def submit(self, c, text='QA-C deterministic request'):
            r = await c.post('/api/requests', data={'text':text}, headers={'Idempotency-Key':uuid4().hex})
            assert r.status_code == 202, (r.status_code, r.text)
            result=r.json()
            rows=await self.graph('MATCH (q:Request {tenant_id:$tenant,id:$id}) RETURN q.active_run_id AS run',id=result['request_id'])
            result['run_id']=rows[0]['run']
            return result

        async def terminal(self, request_id, timeout=45):
            for _ in range(int(timeout*10)):
                rows = await self.graph(
                    "MATCH (q:Request {tenant_id:$tenant,id:$id}) "
                    "MATCH (r:Run {tenant_id:$tenant,id:q.active_run_id}) "
                    "RETURN r.id AS run,r.status AS status,q.status AS request", id=request_id)
                if rows and rows[0]['status'] in {'judgment_saved', 'cancelled', 'failed'}:
                    return rows[0]
                await asyncio.sleep(.1)
            raise AssertionError('run did not settle')

        def worker(self, name):
            return start(name, [sys.executable, str(ROOT/'scripts/e2e/mock_worker.py'),
                          '--tenant', tenant, '--poll-seconds', '.05', '--concurrency', '10'])

    procs, logs = {}, []
    def start(name, args):
        stream = (EVIDENCE / (name+'.log')).open('a')
        logs.append(stream)
        proc = subprocess.Popen(args, cwd=ROOT/'backend', env=os.environ.copy(),
                                stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        procs[name] = proc
        return proc
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    start('redis', [shutil.which('redis-server'), '--port', '11493', '--save', '', '--appendonly', 'no'])
    for port in (11491,11492):
        start('api-'+str(port), [sys.executable,'-m','uvicorn','jevtriage.main:app',
                               '--host','127.0.0.1','--port',str(port),'--no-access-log'])
    try:
        async with httpx.AsyncClient(timeout=2) as c:
            for port in (11491,11492):
                for _ in range(200):
                    try:
                        if (await c.get(f'http://127.0.0.1:{port}/api/ready')).status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(.1)
                else:
                    raise AssertionError(f'QA API {port} failed to start')
        h=Harness()
        h.tenant=tenant
        h.procs=procs
        h.start=start
        yield h
    finally:
        for p in procs.values():
            if p.poll() is None:
                os.killpg(p.pid, signal.SIGTERM)
                try:
                    await asyncio.to_thread(p.wait, timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGKILL)
                    await asyncio.to_thread(p.wait)
        for stream in logs:
            stream.close()
        async def remove(tx):
            await (await tx.run('MATCH (n {tenant_id:$tenant}) DETACH DELETE n', tenant=tenant)).consume()
        await write_tx(tenant, remove)
