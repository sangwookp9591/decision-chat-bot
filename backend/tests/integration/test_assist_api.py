"""Real Neo4j persistence, policy pinning, permissions, fallback and secret containment."""
import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from ildongi.assist import api as assist_api
from ildongi.assist.service import _model_cache
from ildongi.auth.core import Principal, get_principal
from ildongi.config import Settings
from ildongi.db.schema import apply_schema
from ildongi.db.tx import read_tx, write_tx
from ildongi.ingest.store import create_request, get_request_meta
from ildongi.jobs.worker import Worker
from ildongi.judgment import service as judgment_service
from ildongi.judgment.ai_client import AiClient
from ildongi.judgment.store import get_judgment
from ildongi.main import create_app
from ildongi.policy.service import DEFAULT_CONFIG, bootstrap_policy, get_active_snapshot, publish

pytestmark = pytest.mark.asyncio(loop_scope='session')


@pytest_asyncio.fixture(loop_scope='session')
async def tenant():
    value = 'assist_' + uuid4().hex
    await apply_schema()
    await bootstrap_policy(value)
    yield value
    async def cleanup(tx):
        await (await tx.run('MATCH (n {tenant_id:$tenant}) DETACH DELETE n', tenant=value)).consume()
    await write_tx(value, cleanup)


def app_for(tenant, role):
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal(tenant, 'tester', ('IT팀',), frozenset([role]), True)
    return app


@pytest.mark.parametrize('role,read_status,test_status', [('policy_editor', 200, 200), ('operator', 200, 403), ('requester', 403, 403), ('rule_admin', 403, 403)])
async def test_roles_and_model_validation(tenant, role, read_status, test_status, monkeypatch):
    settings = Settings(llm_mode='fake', anthropic_api_key='', openai_api_key='', gemini_api_key='')
    monkeypatch.setattr(assist_api, 'get_settings', lambda: settings)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_for(tenant, role)), base_url='http://test') as client:
        assert (await client.get('/api/assist/providers')).status_code == read_status
        assert (await client.get('/api/assist/providers/anthropic/models')).status_code == read_status
        response = await client.post('/api/assist/providers/anthropic/test', json={'model': 'claude-opus-5-5'})
        assert response.status_code == test_status
        if test_status == 200:
            assert response.json()['error_code'] == 'KEY_MISSING'
            assert not response.json()['ok']
            assert (await client.post('/api/assist/providers/unknown/test', json={'model': 'x'})).status_code == 404
            assert (await client.post('/api/assist/providers/anthropic/test', json={'model': '!'})).status_code == 422
        assert (await client.post('/api/assist/providers/anthropic/test', cookies={'ildongi_session': 'invalid'}, json={'model': 'x'})).status_code == 403


async def test_fake_success_default_list_and_no_secret_in_responses(tenant, monkeypatch):
    secret = 'sk-ant-test-SECRET-12345678901234567890'
    settings = Settings(llm_mode='fake', anthropic_api_key=secret, openai_api_key='', gemini_api_key='')
    monkeypatch.setattr(assist_api, 'get_settings', lambda: settings)
    _model_cache.clear()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_for(tenant, 'policy_editor')), base_url='http://test') as client:
        for path in ('/api/assist/providers', '/api/assist/providers/anthropic/models', '/api/assist/providers/google/models'):
            response = await client.get(path)
            assert response.status_code == 200 and secret not in response.text
        assert (await client.get('/api/assist/providers/google/models')).json()['source'] == 'default'
        response = await client.post('/api/assist/providers/anthropic/test', json={'model': 'claude-opus-5-5'})
        assert response.json()['ok'] and secret not in response.text


async def run(tenant):
    created = await create_request(tenant, 'tester', '공개 데이터로 월별 집계 대시보드를 개발해 주세요.', [],
                                   str(uuid4()), str(uuid4()), datetime.now(UTC).isoformat())
    req = created['request_id']
    rid = (await get_request_meta(tenant, req))['active_run_id']
    async def job(tx):
        return (await (await tx.run('MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id', tenant=tenant, run=rid)).single(strict=True))['id']
    async def handler(ctx):
        await judgment_service.execute_judgment(ctx, AiClient('', mode='mock'))
    await Worker(handlers={'judgment': handler}).process_job(tenant, await read_tx(tenant, job))
    saved = await get_judgment(tenant, req, rid)
    assert saved is not None
    return saved


async def test_run_texts_persist_without_changing_decisions(tenant, monkeypatch, tmp_path):
    secret = 'sk-ant-test-SECRET-12345678901234567890'
    monkeypatch.setattr(judgment_service, 'get_settings', lambda: Settings(llm_mode='fake', anthropic_api_key=secret, data_dir=tmp_path))
    baseline = await run(tenant)
    active, policy = await get_active_snapshot(tenant)
    conf = {**policy, 'llm': {**DEFAULT_CONFIG['llm'], 'provider': 'anthropic', 'model': 'claude-opus-5-5',
                            'features': {'summary': True, 'task_description': True, 'questions': True, 'rule_explanation': True}}}
    await publish(tenant, 'tester', conf, 'LLM fake integration', active, idempotency_key=str(uuid4()))
    saved = await run(tenant)
    j = saved['judgment']
    assert json.loads(j['summary'])['author'] == 'llm:anthropic/claude-opus-5-5'
    assert json.loads(j['versions'])['llm'] == 'anthropic/claude-opus-5-5'
    assert json.loads(j['llm_json'])['calls'][0]['outcome'] == 'ok'
    tasks = [dict(t) for d in saved['drafts'] for t in d['tasks'] if t]
    assert tasks and all(t['description'] and t['description_author'].startswith('llm:') for t in tasks)
    for key in ('ai_need', 'feasibility', 'urgency', 'lead_org', 'eligibility_json'):
        assert j[key] == baseline['judgment'][key]
    assert bool(saved['review']) == bool(baseline['review'])
    assert saved['review']['reasons'] == baseline['review']['reasons']
    assert secret not in json.dumps(j, default=str)
    async def steps(tx):
        return await (await tx.run('MATCH (s:RunStep {tenant_id:$tenant,run_id:$run,name:"글 다듬기"}) RETURN s.output_summary_json AS output', tenant=tenant, run=j['run_id'])).data()
    records = await read_tx(tenant, steps)
    assert records and json.loads(records[0]["output"])["calls"] == json.loads(j["llm_json"])["calls"]
    monkeypatch.setattr(judgment_service, 'get_settings', lambda: Settings(llm_mode='live', anthropic_api_key='', openai_api_key='', gemini_api_key=''))
    fallback = await run(tenant)
    assert json.loads(fallback['judgment']['summary'])['author'] == 'code:extractive@1'
    calls = json.loads(fallback['judgment']['llm_json'])['calls']
    assert all(c['outcome'] in ('fallback', 'skipped') for c in calls)
    for directory in (tmp_path, judgment_service.get_settings().data_dir):
        if directory.exists():
            for pattern in ('*.jsonl', '*.log'):
                for file in directory.rglob(pattern):
                    assert secret not in file.read_text(errors='replace')


async def test_explanation_is_audited_and_rule_body_unchanged(tenant, monkeypatch):
    from ildongi.learning import explain_api
    settings = Settings(llm_mode='fake', anthropic_api_key='', openai_api_key='', gemini_api_key='')
    monkeypatch.setattr(explain_api, 'get_settings', lambda: settings)
    active, policy = await get_active_snapshot(tenant)
    enabled = {**policy, 'llm': {**DEFAULT_CONFIG['llm'], 'provider': 'anthropic',
                               'model': 'claude-opus-5-5', 'features': {'rule_explanation': True}}}
    await publish(tenant, 'tester', enabled, 'enable explanation', active, idempotency_key=str(uuid4()))
    candidate_id = 'cand_' + uuid4().hex
    body = json.dumps({'target': 'lead_org', 'scope': {'all': []}, 'action': {'set': 'IT팀'}})
    async def seed(tx):
        await (await tx.run('CREATE (:RuleCandidate {tenant_id:$tenant,id:$id,proposed_body:$body,rationale:"규칙 사유"})', tenant=tenant, id=candidate_id, body=body)).consume()
    await write_tx(tenant, seed)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_for(tenant, 'operator')), base_url='http://test') as client:
        assert (await client.post(f'/api/learning/candidates/{candidate_id}/explanation')).status_code == 403
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_for(tenant, 'rule_admin')), base_url='http://test') as client:
        response = await client.post(f'/api/learning/candidates/{candidate_id}/explanation')
        assert response.status_code == 200 and response.json()['author'].startswith('llm:anthropic/')
    async def stored(tx):
        row = await (await tx.run('MATCH (c:RuleCandidate {tenant_id:$tenant,id:$id}) MATCH (a:Audit {tenant_id:$tenant,action:"rule.explanation",target_id:$id}) RETURN c.proposed_body AS body,c.explanation AS explanation,c.explanation_usage_json AS usage,count(a) AS audits', tenant=tenant, id=candidate_id)).single(strict=True)
        return dict(row)
    saved = await read_tx(tenant, stored)
    assert saved['body'] == body and saved['explanation'].startswith('[fake]') and saved['audits'] == 1
    assert json.loads(saved['usage'])['input_tokens'] > 0
    active, policy = await get_active_snapshot(tenant)
    disabled = {**policy, 'llm': {**policy['llm'], 'features': {**policy['llm']['features'], 'rule_explanation': False}}}
    await publish(tenant, 'tester', disabled, 'disable explanation', active, idempotency_key=str(uuid4()))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_for(tenant, 'rule_admin')), base_url='http://test') as client:
        response = await client.post(f'/api/learning/candidates/{candidate_id}/explanation')
        assert response.status_code == 422 and response.json()['detail']['code'] == 'LLM_DISABLED'


async def test_policy_editor_can_publish_llm_with_existing_rules_but_cannot_change_rules(tenant):
    from ildongi.auth.core import enforce_csrf
    from ildongi.policy.service import validate_config
    active, snapshot = await get_active_snapshot(tenant)
    rule = {'rule_id': 'R-LEAD_ORG-99', 'version': 1, 'effect': 'rule', 'target': 'lead_org',
            'scope': {'all': [{'text': {'contains_any': ['VPN']}}]}, 'action': {'set': 'IT팀'}}
    prior, errors = validate_config({**snapshot, 'rules': [rule]})
    assert not errors
    async def seed(tx):
        await (await tx.run('MATCH (c:ConfigVersion {tenant_id:$tenant,version:$version}) SET c.config_json=$config', tenant=tenant, version=active, config=json.dumps(prior))).consume()
    await write_tx(tenant, seed)
    changed = {**prior, 'llm': {**DEFAULT_CONFIG['llm'], 'provider': 'anthropic', 'model': 'claude-opus-5-5'}}
    app = app_for(tenant, 'policy_editor')
    app.dependency_overrides[enforce_csrf] = lambda: None  # Authentication/CSRF failure tested separately above.
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        validation = await client.post('/api/policy/validate', json={'config': changed})
        assert validation.status_code == 200 and validation.json()['valid']
        published = await client.post('/api/policy/publish', json={'config': changed, 'reason': 'LLM only', 'expected_active_version': active}, headers={'Idempotency-Key': str(uuid4())})
        assert published.status_code == 200
        assert published.json()['config']['rules'] == prior['rules']
        changed_rules = {**changed, 'rules': []}
        validation = await client.post('/api/policy/validate', json={'config': changed_rules})
        assert not validation.json()['valid']
        assert validation.json()['errors'][0]['code'] == 'RULE_ADMIN_REQUIRED'
        denied = await client.post('/api/policy/publish', json={'config': changed_rules, 'reason': 'forbidden rule change', 'expected_active_version': published.json()['version']}, headers={'Idempotency-Key': str(uuid4())})
        assert denied.status_code == 422 and denied.json()['detail']['code'] == 'RULE_ADMIN_REQUIRED'
