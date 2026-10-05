"""QA-C-02/04/06: real storage and transport boundary regression checks."""
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from jevtriage.auth.core import Principal, get_principal
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.ingest.store import create_request, get_request_meta
from jevtriage.jobs.worker import Worker
from jevtriage.judgment.jev_client import JevClient
from jevtriage.judgment.service import execute_judgment
from jevtriage.learning.shadow import validate_rules
from jevtriage.main import create_app
from jevtriage.policy.service import DEFAULT_CONFIG, bootstrap_policy
from tests.integration.test_review_assignment import sample

pytestmark = pytest.mark.asyncio(loop_scope='session')


@pytest_asyncio.fixture(loop_scope='session')
async def tenant():
    value = 'qa_c_fix_'+uuid4().hex
    await apply_schema()
    async def seed(tx):
        await (await tx.run(
            'UNWIND ["ai", "it", "business"] AS org '
            'CREATE (:Org {tenant_id:$tenant,id:$tenant+"-"+org,name:org})',
            tenant=value)).consume()
    await write_tx(value, seed)
    yield value
    async def cleanup(tx):
        await (await tx.run('MATCH (n {tenant_id:$tenant}) DETACH DELETE n',
                            tenant=value)).consume()
    await write_tx(value, cleanup)


def samples():
    # Key-shaped synthetic sample is assembled at runtime; no key literal in source.
    return ['qa.canary@example.invalid', '010-1234-5678', '900101-1234567',
            '4111 1111 1111 1111', '_'.join(('sk', 'test', 'QACanary'+'0123456789'*3))]


class CaptureClient(JevClient):
    def __init__(self):
        super().__init__('unused', mode='mock')
        self.payloads = []

    def ask(self, state, questions):
        self.payloads.append(json.dumps({'state': state, 'questions': questions}, ensure_ascii=False))
        return super().ask(state, questions)


@pytest.mark.parametrize('kind', ['normal', 'shadow'])
async def test_every_model_payload_masks_five_categories(tenant, kind):
    await bootstrap_policy(tenant)
    text = '\n'.join(samples())
    rule = {'schema': 'rule-v1', 'rule_id': 'R-QA-C', 'version': 1, 'effect': 'context',
            'target': 'ai_need', 'scope': {'all': []}, 'action': {'set': '혼합'},
            'context_text': text}
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    config['learning']['shadow_max_calls'] = 100
    config['rules'] = [rule]
    async def seed(tx):
        await (await tx.run(
            "CREATE (:RuleVersion {tenant_id:$tenant,id:'R-QA-C@1',body:$body,status:'validating'}) "
            "WITH 1 AS ignored MATCH (c:ConfigVersion {tenant_id:$tenant,status:'active'}) "
            "SET c.config_json=$config",
            tenant=tenant, body=json.dumps(rule), config=json.dumps(config))).consume()
    await write_tx(tenant, seed)
    client = CaptureClient()
    if kind == 'normal':
        created = await create_request(tenant, 'tester', text, [], str(uuid4()), str(uuid4()),
                                       datetime.now(UTC).isoformat())
        meta = await get_request_meta(tenant, created['request_id'])
        async def job(tx):
            return (await (await tx.run(
                'MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id',
                tenant=tenant, run=meta['active_run_id'])).single(strict=True))['id']
        async def handler(ctx):
            await execute_judgment(ctx, client)
        await Worker(handlers={'judgment': handler}).process_job(tenant, await read_tx(tenant, job))
    else:
        async def shadow_seed(tx):
            await (await tx.run(
                "CREATE (:Request {tenant_id:$tenant,id:'request',org_ids:[]}) "
                "CREATE (:InputRevision {tenant_id:$tenant,id:'revision',request_id:'request',text:$text}) "
                "CREATE (:Judgment {tenant_id:$tenant,id:'judgment',request_id:'request',revision_id:'revision',"
                "run_id:'run',created_at:datetime(),ai_need:'필요',feasibility:'가능',urgency:'일반',lead_org:'AI팀'})",
                tenant=tenant, text=text)).consume()
        await write_tx(tenant, shadow_seed)
        result = await validate_rules(tenant, 'tester', 'R-QA-C', 1,
                                      datetime.now(UTC)-timedelta(minutes=1),
                                      datetime.now(UTC)+timedelta(minutes=1), client=client)
        assert result['status'] == 'completed'
    assert client.payloads
    assert all(value not in payload for payload in client.payloads for value in samples())
    assert any('operating_guidance' in payload for payload in client.payloads)


@pytest.mark.parametrize('org_value', ['IT팀', '검토자', 'AI팀', '현업', 'id'])
async def test_authorized_review_survives_100_newer_other_org_reviews(tenant, org_value):
    target_org = {'IT팀': 'it', '검토자': 'ai', 'AI팀': 'ai', '현업': 'business', 'id': 'it'}[org_value]
    stored_org = tenant+'-it' if org_value == 'id' else org_value
    async def seed(tx):
        await (await tx.run(
            "UNWIND range(0,100) AS i "
            "CREATE (q:Request {tenant_id:$tenant,id:'q_'+toString(i),created_by:'other',"
            "org_ids:[],shared_org_ids:[],active_run_id:'run_'+toString(i),latest_revision_id:'rev_'+toString(i)}) "
            "CREATE (:Review {tenant_id:$tenant,id:'v_'+toString(i),request_id:q.id,"
            "run_id:q.active_run_id,revision_id:q.latest_revision_id,status:'pending',"
            "draft_version:1,review_version:1,reasons:'[]',created_at:datetime()+duration({seconds:i}),"
            "required_reviewer_org:CASE WHEN i=0 THEN $org ELSE $tenant+'-unrelated' END})",
            tenant=tenant, org=stored_org)).consume()
    await write_tx(tenant, seed)
    principal = Principal(tenant, 'reviewer', (tenant+'-'+target_org,), frozenset({'reviewer'}))
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: principal
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        assert (await client.get('/api/reviews/v_0')).status_code == 200
        response = await client.get('/api/reviews')
        assert response.status_code == 200
        assert 'v_0' in [row['id'] for row in response.json()['reviews']]
        app.dependency_overrides[get_principal] = lambda: Principal(
            tenant, 'operator', principal.org_ids, frozenset({'operator'}))
        assert (await client.get('/api/reviews')).json()['reviews'] == []


@pytest.mark.parametrize('changes', [
    {'classifications': ['qa-invalid']}, {'draft_tasks': ['qa-invalid']},
    {'draft_tasks': [{'draft_task_id': 'draft-1', 'lead_org': ['qa-invalid']}]},
    {'classifications': {'ai_need': 'qa-invalid'}},
    {'draft_tasks': [{'draft_task_id': 'draft-1', 'predecessors': [1]}]},
    {'draft_tasks': [{'draft_task_id': 'draft-1', 'method': ['qa-invalid']}]},
])
async def test_invalid_nested_review_changes_preserve_review(tenant, changes):
    principal, review_id, command = await sample(tenant)
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: principal
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
                                 base_url='http://test') as client:
        before = (await client.get('/api/reviews/'+review_id)).json()
        response = await client.post('/api/reviews/'+review_id+'/decision',
                                     json={**command, 'action': 'approve_with_changes',
                                           'changes': changes, 'reason': 'test invalid types'},
                                     headers={'Idempotency-Key': str(uuid4())})
        assert response.status_code == 422, response.text
        assert (await client.get('/api/reviews/'+review_id)).json() == before
    async def check(tx):
        return (await (await tx.run(
            'MATCH (n {tenant_id:$tenant}) WHERE n:Assignment OR n:Task OR n:Correction '
            'OR n:ReviewDecision RETURN count(n) AS count', tenant=tenant)).single())['count']
    assert await read_tx(tenant, check) == 0
