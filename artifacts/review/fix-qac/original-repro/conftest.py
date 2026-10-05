"""Same QA tenant operations via ASGI, real Neo4j, and real Worker.process_job.

No API subprocesses or extra databases; only the owned random tenant is removed.
"""
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from jevtriage.auth.core import Principal, get_principal
from jevtriage.config import get_settings
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.jobs.worker import Worker
from jevtriage.judgment.jev_client import JevClient
from jevtriage.judgment.service import execute_judgment
from jevtriage.main import create_app
from jevtriage.policy.service import bootstrap_policy


@pytest_asyncio.fixture(scope='module', loop_scope='module')
async def runtime(tmp_path_factory):
    patch = pytest.MonkeyPatch()
    patch.setenv('DATA_DIR', str(tmp_path_factory.mktemp('qac-original-data')))
    get_settings.cache_clear()
    tenant = 'qa_c_original_'+uuid4().hex
    await apply_schema()
    await bootstrap_policy(tenant)
    async def seed(tx):
        await (await tx.run(
            'UNWIND ["ai", "it", "business"] AS org '
            'CREATE (:Org {tenant_id:$tenant,id:$tenant+"-"+org,name:org})', tenant=tenant)).consume()
    await write_tx(tenant, seed)
    principal = Principal(tenant, 'qa-user', tuple(tenant+'-'+x for x in ('ai','it','business')),
                          frozenset({'requester','reviewer','operator'}), True)
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: principal
    # CSRF dependency is still checked against a deterministic test session.
    from jevtriage.auth import core
    original_session = core.session_principal
    async def session(_token):
        return principal, 'csrf-ok'
    core.session_principal = session
    class Harness:
        async def graph(self, query, **params):
            async def op(tx):
                return await (await tx.run(query, tenant=tenant, **params)).data()
            return await read_tx(tenant, op)

        async def write(self, query, **params):
            async def op(tx):
                return await (await tx.run(query, tenant=tenant, **params)).data()
            return await write_tx(tenant, op)

        async def login(self):
            client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
                                       base_url='http://test', headers={'X-CSRF-Token':'csrf-ok'})
            client.cookies.set('jev_session','qa-session')
            client.cookies.set('jev_csrf','csrf-ok')
            return client

        async def submit(self, client, text):
            response = await client.post('/api/requests', data={'text':text},
                                          headers={'Idempotency-Key':uuid4().hex})
            assert response.status_code == 202, response.text
            result = response.json()
            rows = await self.graph('MATCH (q:Request {tenant_id:$tenant,id:$id}) '
                                    'RETURN q.active_run_id AS run', id=result['request_id'])
            result['run_id'] = rows[0]['run']
            return result

        def worker(self, name):
            # Original probe requires this lifecycle handle; terminal() drives the real worker.
            class Finished:
                def poll(self):
                    return 0
            return Finished()

        async def terminal(self, request_id, timeout=90):
            rows = await self.graph('MATCH (q:Request {tenant_id:$tenant,id:$id}) '
                                    'MATCH (j:Job {tenant_id:$tenant,run_id:q.active_run_id}) '
                                    'RETURN j.id AS id', id=request_id)
            assert len(rows) == 1
            async def handler(ctx):
                await execute_judgment(ctx, JevClient('unused', mode='mock'))
            await Worker(handlers={'judgment':handler}).process_job(tenant, rows[0]['id'])
            rows = await self.graph('MATCH (q:Request {tenant_id:$tenant,id:$id}) '
                                    'MATCH (r:Run {tenant_id:$tenant,id:q.active_run_id}) '
                                    'RETURN r.status AS status', id=request_id)
            assert rows[0]['status'] == 'judgment_saved'
    harness = Harness()
    harness.tenant = tenant
    try:
        yield harness
    finally:
        core.session_principal = original_session
        await harness.write('MATCH (n {tenant_id:$tenant}) DETACH DELETE n')
        patch.undo()
        get_settings.cache_clear()
