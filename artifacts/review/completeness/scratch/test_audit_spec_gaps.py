"""Acceptance reproduction: spec/04 requires labeled counts for effect comparisons."""
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import httpx

from jevtriage.auth.core import Principal, get_principal
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.ingest.store import create_request
from jevtriage.learning.effects import rule_effects
from jevtriage.policy.service import bootstrap_policy
from jevtriage.main import create_app


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
async def test_persisted_evidence_node_has_creation_time_and_creator():
    tenant = 'audit_spec_metadata_' + uuid4().hex
    await apply_schema()

    async def evidence(tx):
        row = await (await tx.run(
            'MATCH (e:EvidenceSpan {tenant_id:$tenant}) RETURN properties(e) AS span LIMIT 1',
            tenant=tenant,
        )).single(strict=True)
        return row['span']

    async def cleanup(tx):
        await (await tx.run('MATCH (n {tenant_id:$tenant}) DETACH DELETE n', tenant=tenant)).consume()

    try:
        await create_request(tenant, 'audit-user', '시설 점검 입력과 확인 요청입니다.', [],
                             'audit-key', 'audit-hash', datetime.now(UTC).isoformat())
        span = await read_tx(tenant, evidence)
        assert span.get('created_at') is not None, '08_LEARNING_LOOP.md:48 requires creation time on every node'
        assert any(span.get(key) for key in ('created_by', 'actor', 'author')), '08_LEARNING_LOOP.md:48 requires creator on every node'
    finally:
        await write_tx(tenant, cleanup)
