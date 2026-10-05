"""Acceptance reproduction: spec/04 requires labeled counts for effect comparisons."""
from uuid import uuid4

import httpx
import pytest

from jevtriage.auth.core import Principal, get_principal
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import write_tx
from jevtriage.learning.effects import rule_effects
from jevtriage.main import create_app
from jevtriage.policy.service import bootstrap_policy


@pytest.mark.asyncio(loop_scope='session')
async def test_rule_effect_comparisons_expose_human_labeled_sample_counts():
    tenant = 'audit_spec_' + uuid4().hex
    rule_id = 'R-AI_NEED-97'
    await apply_schema()
    await bootstrap_policy(tenant)

    async def seed(tx):
        await (await tx.run(
            'CREATE (r:RuleVersion {tenant_id:$tenant,id:$id,rule_id:$rule}) '
            'CREATE (c:ConfigVersion {tenant_id:$tenant,id:$config,version:2,created_at:datetime()}) '
            'CREATE (r)-[:PUBLISHED_IN]->(c)',
            tenant=tenant, id=rule_id + '@1', rule=rule_id, config='cfg_' + tenant + '_2',
        )).consume()

    async def cleanup(tx):
        await (await tx.run('MATCH (n {tenant_id:$tenant}) DETACH DELETE n', tenant=tenant)).consume()

    try:
        await write_tx(tenant, seed)
        result = await rule_effects(tenant, rule_id, 7)
        comparisons = [*result['before_after'].values(), *result['groups'].values()]
        cohorts = [value for value in comparisons if isinstance(value, dict)]
        assert len(cohorts) == 4
        for cohort in cohorts:
            assert 'labeled_count' in cohort, '04_OBSERVATORY.md:39 requires human-labeled sample count for each comparison'
            assert cohort['labeled_count'] == 0
    finally:
        await write_tx(tenant, cleanup)


@pytest.mark.asyncio(loop_scope='session')
@pytest.mark.parametrize('role', ['reviewer', 'operator'])
async def test_rule_read_allowed_for_scoped_reviewer_and_operator(role):
    tenant = 'audit_spec_read_' + uuid4().hex
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal(
        tenant, 'audit-reader', (), frozenset({role}),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url='http://audit',
    ) as client:
        response = await client.get('/api/learning/rules')
    assert response.status_code == 200, (
        f'08_LEARNING_LOOP.md:91 permits scoped {role} read; '
        f'actual status={response.status_code}'
    )




@pytest.mark.asyncio(loop_scope='session')
@pytest.mark.parametrize('role,org,expected', [
    ('reviewer', 'IT팀', 200), ('reviewer', '현업', 404),
    ('operator', '현업', 200), ('rule_admin', '현업', 200),
    ('requester', 'IT팀', 403),
])
async def test_rule_read_scope_and_write_matrix(monkeypatch, role, org, expected):
    from jevtriage.learning import effects_api, rules_api

    row = {'rule_id': 'R-AI_NEED-01', 'versions': [
        {'version': 1, 'body': {'scope': {'all': [{'requester_org': 'IT팀'}]},
                               'source_text': 'restricted raw source'}}]}

    async def detail(*args):
        return row

    async def listing(*args):
        return [{'rule_id': 'R-AI_NEED-01', 'latest_version': 1, 'version_count': 1}]

    async def effects(*args):
        return {'sample_count': 0}

    monkeypatch.setattr(rules_api, 'rule_detail', detail)
    monkeypatch.setattr(rules_api, 'list_rules', listing)
    monkeypatch.setattr(effects_api, 'rule_detail', detail)
    monkeypatch.setattr(effects_api, 'rule_effects', effects)
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal(
        'read-matrix', 'reader', (org,), frozenset({role}), False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/api/learning/rules/R-AI_NEED-01')
        assert response.status_code == expected
        assert 'restricted raw source' not in response.text
        assert (await client.get('/api/learning/rules/R-AI_NEED-01/effects')).status_code == expected
        listing_response = await client.get('/api/learning/rules')
        if expected == 404:
            assert listing_response.json() == {'rules': []}
        if role != 'rule_admin':
            response = await client.post('/api/learning/rules/R-AI_NEED-01/versions',
                                         json={'decision_id': 'd', 'reason': 'test'})
            assert response.status_code == 403


@pytest.mark.asyncio(loop_scope='session')
async def test_labels_count_approved_runs_once_and_exclude_pending_rejected_and_shadow():
    tenant = 'labels_' + uuid4().hex
    await apply_schema()
    await bootstrap_policy(tenant)

    async def seed(tx):
        await (await tx.run(
            "CREATE (rv:RuleVersion {tenant_id:$tenant,id:'R-AI_NEED-98@1',rule_id:'R-AI_NEED-98'}) "
            "CREATE (cfg:ConfigVersion {tenant_id:$tenant,id:$cfg,version:2,created_at:datetime()}) "
            "CREATE (rv)-[:PUBLISHED_IN]->(cfg) WITH rv "
            "UNWIND range(0,4) AS i "
            "CREATE (q:Request {tenant_id:$tenant,id:$tenant+'-req_'+toString(i),org_ids:[CASE WHEN i%2=0 THEN 'it' ELSE 'other' END]}) "
            "CREATE (r:Run {tenant_id:$tenant,id:$tenant+'-run_'+toString(i),started_at:datetime()+duration({hours:1}),"
            "request_id:q.id,run_kind:CASE WHEN i=4 THEN 'shadow' ELSE 'production' END,status:'completed'}) "
            "CREATE (h:ReviewDecision {tenant_id:$tenant,id:$tenant+'-dec_'+toString(i),run_id:r.id,"
            "action:CASE i WHEN 0 THEN 'approve' WHEN 1 THEN 'approve_with_changes' "
            "WHEN 2 THEN 'reject' ELSE 'pending' END}) "
            "CREATE (s:RunStep {tenant_id:$tenant,id:$tenant+'-step_'+toString(i),run_id:r.id}) "
            "CREATE (s)-[:APPLIED {outcome:CASE WHEN i=0 THEN 'used' ELSE 'out_of_scope' END}]->(rv) "
            "WITH r,i WHERE i=0 CREATE (:ReviewDecision {tenant_id:$tenant,id:$tenant+'-duplicate',run_id:r.id,action:'approve'})",
            tenant=tenant, cfg='cfg_'+tenant,
        )).consume()
    async def cleanup(tx):
        await (await tx.run('MATCH (n {tenant_id:$tenant}) DETACH DELETE n', tenant=tenant)).consume()
    try:
        await write_tx(tenant, seed)
        result = await rule_effects(tenant, 'R-AI_NEED-98', 7)
        assert result['before_after']['after']['sample_count'] == 4
        assert result['before_after']['after']['labeled_count'] == 2
        assert result['groups']['used']['labeled_count'] == 1
        assert result['groups']['out_of_scope']['labeled_count'] == 1
        assert result['effect'] == 'insufficient_sample'
        reviewer = Principal(tenant, 'reviewer', ('it',), frozenset({'reviewer'}))
        scoped = await rule_effects(tenant, 'R-AI_NEED-98', 7, reviewer)
        assert scoped['before_after']['after']['sample_count'] == 2
        assert scoped['before_after']['after']['labeled_count'] == 1
    finally:
        await write_tx(tenant, cleanup)
