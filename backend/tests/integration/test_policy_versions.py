import asyncio
from uuid import uuid4

import pytest
import pytest_asyncio

from ildongi.db.driver import get_driver
from ildongi.policy.service import (
    PolicyError,
    bootstrap_policy,
    get_active_snapshot,
    get_version,
    publish,
    rollback,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def tenant():
    value = f"policy_{uuid4().hex}"
    await bootstrap_policy(value)
    yield value
    driver = await get_driver()
    async with driver.session() as session:
        await (await session.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=value)).consume()


def config(**updates):
    from ildongi.policy.service import DEFAULT_CONFIG
    return {**DEFAULT_CONFIG, **updates}


async def test_learning_config_defaults_and_bounds():
    from ildongi.policy.service import DEFAULT_CONFIG, validate_config
    assert DEFAULT_CONFIG["learning"] == {
        "min_support": 3, "min_effect_sample": 20,
        "shadow_max_calls": 20, "effect_window_days": 7,
    }
    valid, errors = validate_config(config(learning={
        "min_support": 2, "min_effect_sample": 5,
        "shadow_max_calls": 0, "effect_window_days": 90,
    }))
    assert not errors and valid["learning"]["shadow_max_calls"] == 0
    for bad in ({"min_support": 1}, {"min_effect_sample": 4},
                {"shadow_max_calls": 201}, {"effect_window_days": 0}):
        _, errors = validate_config(config(learning=bad))
        assert errors and errors[0]["code"] == "SCHEMA_INVALID"


async def test_publish_diff_audit_snapshot_and_rollback(tenant):
    version, snapshot = await get_active_snapshot(tenant)
    assert version == 1 and snapshot["auto_assign"] is False
    updated = await publish(tenant, "editor", config(evidence_noul_threshold=.7), "조정", 1, idempotency_key="publish-1")
    assert updated["version"] == 2
    assert updated["diff"]["evidence_noul_threshold"] == {"before": .6, "after": .7}
    # A previously acquired snapshot remains an immutable value.
    assert snapshot["evidence_noul_threshold"] == .6
    assert (await get_version(tenant, 1))["status"] == "superseded"
    rolled = await rollback(tenant, "editor", 1, "원복", 2, idempotency_key="rollback-1")
    assert rolled["version"] == 3
    assert rolled["config"]["evidence_noul_threshold"] == .6
    async def audit(tx):
        row = await (await tx.run("MATCH (a:Audit {tenant_id:$tenant, action:'policy.publish'}) RETURN count(a) AS n", tenant=tenant)).single(strict=True)
        return row["n"]
    from ildongi.db.tx import read_tx
    assert await read_tx(tenant, audit) == 2


async def test_reject_unsafe_publish_and_rollback(tenant):
    with pytest.raises(PolicyError) as exc:
        await publish(tenant, "editor", config(risk_clear_max=.8), "unsafe", 1, idempotency_key="unsafe")
    assert exc.value.code == "RISK_BAND_TOO_PERMISSIVE"
    # Historical unsafe content is revalidated before rollback publication.
    import json

    from ildongi.db.tx import write_tx
    from ildongi.policy.service import DEFAULT_CONFIG
    unsafe = {**DEFAULT_CONFIG, "risk_clear_max": .8}
    async def seed(tx):
        await (await tx.run("CREATE (:ConfigVersion {id:$id, tenant_id:$tenant, version:8, status:'superseded', created_by:'old', reason:'legacy', config_json:$json, diff_json:'{}', created_at:datetime()})", id=f"bad_{tenant}", tenant=tenant, json=json.dumps(unsafe))).consume()
    await write_tx(tenant, seed)
    with pytest.raises(PolicyError) as rollback_exc:
        await rollback(tenant, "editor", 8, "unsafe rollback", 1, idempotency_key="rollback-bad")
    assert rollback_exc.value.code == "RISK_BAND_TOO_PERMISSIVE"


async def test_safe_auto_assign_policy_can_be_published_and_reverted():
    from ildongi.db.tx import write_tx
    tenant = f"policy_auto_{uuid4().hex}"
    await bootstrap_policy(tenant)
    try:
        enabled = await publish(tenant, "editor", config(auto_assign=True),
                                "안전 조건을 모두 재검증하여 자동 배정", 1,
                                idempotency_key="auto-enable")
        assert enabled["version"] == 2 and enabled["config"]["auto_assign"] is True
        reverted = await rollback(tenant, "editor", 1, "자동 배정 중지", 2,
                                  idempotency_key="auto-disable")
        assert reverted["version"] == 3 and reverted["config"]["auto_assign"] is False
    finally:
        async def cleanup(tx):
            await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=tenant)).consume()
        await write_tx(tenant, cleanup)


async def test_concurrent_publish_expected_version_conflict(tenant):
    body = config(evidence_noul_threshold=.7)
    results = await asyncio.gather(*(publish(tenant, f"e{i}", body, "race", 1, idempotency_key=f"race-{i}") for i in range(2)), return_exceptions=True)
    assert sum(not isinstance(item, Exception) for item in results) == 1
    failures = [item for item in results if isinstance(item, Exception)]
    assert len(failures) == 1 and isinstance(failures[0], PolicyError) and failures[0].status_code == 409


async def test_publish_without_policy_editor_is_forbidden():
    from fastapi.testclient import TestClient

    from ildongi.auth.core import Principal, enforce_csrf, get_principal
    from ildongi.main import create_app
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal("tenant", "reviewer", (), frozenset({"reviewer"}))
    app.dependency_overrides[enforce_csrf] = lambda: None
    with TestClient(app) as client:
        response = client.post("/api/policy/publish", headers={"Idempotency-Key": "denied"}, json={"config": config(), "reason": "test", "expected_active_version": 0})
    assert response.status_code == 403
