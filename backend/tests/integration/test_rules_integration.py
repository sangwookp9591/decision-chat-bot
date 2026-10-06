"""Rule lifecycle and real Neo4j application contracts."""
import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from ildongi.auth.core import Principal, enforce_csrf, get_principal
from ildongi.db.driver import close_driver
from ildongi.db.schema import apply_schema
from ildongi.db.tx import read_tx, write_tx
from ildongi.ingest.store import create_request, get_request_meta
from ildongi.jobs.worker import Worker
from ildongi.judgment.ai_client import AiClient
from ildongi.judgment.service import execute_judgment
from ildongi.judgment.store import get_judgment
from ildongi.learning.apply import apply_rules, validate_rule
from ildongi.learning.rules import (
    change_publication,
    create_version,
    decide_candidate,
    mark_validated,
    rule_detail,
)
from ildongi.main import create_app
from ildongi.policy.service import PolicyError, bootstrap_policy, get_active_snapshot

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def tenant():
    value = f"rules_{uuid4().hex}"
    await apply_schema()
    await bootstrap_policy(value)
    yield value
    async def cleanup(tx):
        await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=value)).consume()
    await write_tx(value, cleanup)


def proposed(candidate_id, *, scope=None, action=None, effect="rule", context_text=None,
             target="ai_need"):
    return {"schema": "rule-v1", "rule_id": "R-AI_NEED-01", "version": 1,
            "effect": effect, "target": target, "scope": scope or {"all": []},
            "action": action or {"set": "혼합"}, "candidate_id": candidate_id,
            "decision_id": "pending", **({"context_text": context_text} if context_text else {})}


async def seed_candidate(tenant, *, scope=None, action=None, effect="rule", context_text=None,
                         target="ai_need"):
    candidate_id = f"cand_{uuid4().hex}"
    async def op(tx):
        await (await tx.run("CREATE (:RuleCandidate {id:$id,tenant_id:$tenant,status:'제안',proposed_body:$body,created_at:datetime()})",
                            id=candidate_id, tenant=tenant,
                            body=json.dumps(proposed(candidate_id, scope=scope, action=action,
                                                     effect=effect, context_text=context_text,
                                                     target=target)))).consume()
    await write_tx(tenant, op)
    return candidate_id


async def validated_version(tenant, candidate_id, rule_id="R-AI_NEED-01"):
    decided = await decide_candidate(tenant, "admin", candidate_id, "approve", None, "검토", str(uuid4()))
    created = await create_version(tenant, "admin", rule_id, decided["decision_id"], {}, "생성", str(uuid4()))
    version = created["version"]
    validation_id = f"val_{uuid4().hex}"
    async def seed(tx):
        await (await tx.run("MATCH (r:RuleVersion {tenant_id:$tenant,id:$rule}) CREATE (v:ValidationRun {id:$id,tenant_id:$tenant,status:'completed',side_effects:0,created_at:datetime()})-[:VALIDATES]->(r)",
                            tenant=tenant, rule=f"{rule_id}@{version}", id=validation_id)).consume()
    await write_tx(tenant, seed)
    await mark_validated(tenant, "admin", rule_id, version, validation_id, "부작용 없음", str(uuid4()))
    return version


async def test_role_matrix_and_state_transitions(tenant):
    candidate = await seed_candidate(tenant)
    app = create_app()
    app.dependency_overrides[enforce_csrf] = lambda: None
    for role in ("requester", "reviewer", "operator", "policy_editor"):
        app.dependency_overrides[get_principal] = lambda role=role: Principal(tenant, role, (), frozenset({role}))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            for method, path, body in (
                ("post", f"/api/learning/candidates/{candidate}/decision", {"action": "approve", "reason": "검토"}),
                ("post", "/api/learning/rules/R-AI_NEED-01/versions", {"decision_id": "unknown", "reason": "생성"}),
                ("get", "/api/learning/rules", None),
            ):
                response = await client.request(method, path, json=body)
                expected = 200 if method == "get" and role in {"reviewer", "operator"} else 403
                assert response.status_code == expected
    app.dependency_overrides[get_principal] = lambda: Principal(tenant, "admin", (), frozenset({"rule_admin"}))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/learning/candidates/{candidate}/decision", headers={"Idempotency-Key": "decision-1"}, json={"action": "approve", "reason": "검토"})
        assert response.status_code == 200, response.text
        decision_id = response.json()["decision_id"]
        response = await client.post("/api/learning/rules/R-AI_NEED-01/versions", headers={"Idempotency-Key": "version-1"}, json={"decision_id": decision_id, "reason": "생성"})
        assert response.status_code == 200, response.text
        version = response.json()["version"]
        response = await client.post(f"/api/learning/rules/R-AI_NEED-01/versions/{version}/publish", headers={"Idempotency-Key": "publish-before-validation"}, json={"expected_active_config_version": 1, "reason": "게시"})
        assert response.status_code == 409
        response = await client.post(f"/api/learning/rules/R-AI_NEED-01/versions/{version}/mark-validated", headers={"Idempotency-Key": "fake-validation"}, json={"validation_id": "val_missing", "reason": "검증"})
        assert response.status_code == 409
    rejected = await seed_candidate(tenant)
    decision = await decide_candidate(tenant, "admin", rejected, "reject", None, "기각", str(uuid4()))
    with pytest.raises(PolicyError):
        await create_version(tenant, "admin", "R-AI_NEED-02", decision["decision_id"], {}, "생성", str(uuid4()))


async def test_safety_validation_and_conflict():
    base = proposed("cand_x")
    for target, action in (("feasibility", {"set": "가능"}), ("urgency", {"set": "일반"}),
                           ("review_route", {"set": "none"})):
        with pytest.raises(ValueError):
            validate_rule({**base, "target": target, "action": action})
    initial = {"classifications": {"ai_need": "정보 부족", "feasibility": "정보 부족", "urgency": "판단 보류", "lead_org": "미정"}}
    first = {**base, "rule_id": "R-AI_NEED-01", "version": 1, "action": {"set": "혼합"}}
    second = {**base, "rule_id": "R-AI_NEED-02", "version": 1, "action": {"set": "필요"}}
    outside = {**base, "rule_id": "R-AI_NEED-03", "scope": {"all": [{"field": "urgency", "op": "eq", "value": "긴급"}]}}
    result, applications = apply_rules(initial, [first, second, outside])
    assert result["classifications"]["ai_need"] == "필요"
    assert [a["outcome"] for a in applications] == ["conflict", "used", "out_of_scope"]
    assert initial["classifications"]["ai_need"] == "정보 부족"


async def test_publication_application_stop_revert_and_restart(tenant):
    candidate = await seed_candidate(tenant, scope={"all": [{"field": "ai_need", "op": "eq", "value": "정보 부족"}]})
    version = await validated_version(tenant, candidate)
    frozen = await create_request(tenant, "tester", "게시 전 요청입니다.", [], str(uuid4()), str(uuid4()), datetime.now(UTC).isoformat())
    frozen_request = frozen["request_id"]
    frozen_run = (await get_request_meta(tenant, frozen_request))["active_run_id"]
    async def fix_old(tx):
        await (await tx.run("MATCH (r:Run {tenant_id:$tenant,id:$run}) SET r.versions_json=$versions", tenant=tenant, run=frozen_run, versions=json.dumps({"config": 1, "policy": 1}))).consume()
    await write_tx(tenant, fix_old)
    published = await change_publication(tenant, "admin", "R-AI_NEED-01", "publish", version, 1, "게시", str(uuid4()))
    assert published["config_version"] == 2
    async def job_for(run):
        async def job(tx):
            return (await (await tx.run("MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id", tenant=tenant, run=run)).single(strict=True))["id"]
        return await read_tx(tenant, job)
    async def handler(ctx):
        await execute_judgment(ctx, AiClient("", mode="mock"))
    await Worker(handlers={"judgment": handler}).process_job(tenant, await job_for(frozen_run))
    frozen_saved = await get_judgment(tenant, frozen_request, frozen_run)
    assert frozen_saved is not None and json.loads(frozen_saved["judgment"]["rule_effects"]) == []
    created = await create_request(tenant, "tester", "요청입니다.", [], str(uuid4()), str(uuid4()), datetime.now(UTC).isoformat())
    request_id = created["request_id"]
    run_id = (await get_request_meta(tenant, request_id))["active_run_id"]
    errors = []
    async def handler(ctx):
        try:
            await execute_judgment(ctx, AiClient("", mode="mock"))
        except Exception as exc:
            errors.append(repr(exc))
            raise
    await Worker(handlers={"judgment": handler}).process_job(tenant, await job_for(run_id))
    saved = await get_judgment(tenant, request_id, run_id)
    if saved is None:
        async def diagnostic(tx):
            return await (await tx.run("MATCH (r:Run {tenant_id:$tenant,id:$run}) RETURN r.status AS status,r.error_class AS error", tenant=tenant, run=run_id)).single(strict=True)
        raise AssertionError(f"Judgment absent: {dict(await read_tx(tenant, diagnostic))}, {errors}")
    assert saved["judgment"]["ai_need"] == "혼합"
    effects = json.loads(saved["judgment"]["rule_effects"])
    assert effects[0]["outcome"] == "used"
    assert effects[0]["before"] == "정보 부족" and effects[0]["after"] == "혼합"
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal(tenant, "tester", (), frozenset({"requester"}))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/requests/{request_id}/judgment")
        assert response.status_code == 200
        public_effect = response.json()["rule_effects"][0]
        assert public_effect["rule_version"] == f"R-AI_NEED-01@{version}"
        assert public_effect["effect"] == "rule" and public_effect["config_version"] == 2
    async def relationship(tx):
        return await (await tx.run("MATCH (s:RunStep {tenant_id:$tenant,run_id:$run})-[a:APPLIED]->(r:RuleVersion {tenant_id:$tenant}) RETURN s.kind AS kind,a.outcome AS outcome,r.id AS rule", tenant=tenant, run=run_id)).single(strict=True)
    applied = await read_tx(tenant, relationship)
    assert applied["kind"] == "rule" and applied["outcome"] == "used"
    await close_driver()
    assert (await rule_detail(tenant, "R-AI_NEED-01"))["versions"][0]["application_count"] == 1
    stopped = await change_publication(tenant, "admin", "R-AI_NEED-01", "stop", None, 2, "중단", str(uuid4()))
    assert stopped["config_version"] == 3 and not (await get_active_snapshot(tenant))[1]["rules"]
    later = await create_request(tenant, "tester", "중단 후 요청입니다.", [], str(uuid4()), str(uuid4()), datetime.now(UTC).isoformat())
    later_run = (await get_request_meta(tenant, later["request_id"]))["active_run_id"]
    await Worker(handlers={"judgment": handler}).process_job(tenant, await job_for(later_run))
    later_saved = await get_judgment(tenant, later["request_id"], later_run)
    assert later_saved is not None and json.loads(later_saved["judgment"]["rule_effects"]) == []
    reverted = await change_publication(tenant, "admin", "R-AI_NEED-01", "revert", version, 3, "되돌리기", str(uuid4()))
    assert reverted["config_version"] == 4 and reverted["rules"][0]["version"] == version
    assert (await rule_detail(tenant, "R-AI_NEED-01"))["versions"][0]["application_count"] == 1


async def test_out_of_scope_recorded(tenant):
    candidate = await seed_candidate(tenant, scope={"all": [{"field": "urgency", "op": "eq", "value": "긴급"}]})
    version = await validated_version(tenant, candidate)
    await change_publication(tenant, "admin", "R-AI_NEED-01", "publish", version, 1, "게시", str(uuid4()))
    created = await create_request(tenant, "tester", "일반 요청입니다.", [], str(uuid4()), str(uuid4()), datetime.now(UTC).isoformat())
    run_id = (await get_request_meta(tenant, created["request_id"]))["active_run_id"]
    async def job(tx):
        return (await (await tx.run("MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id", tenant=tenant, run=run_id)).single(strict=True))["id"]
    async def handler(ctx):
        await execute_judgment(ctx, AiClient("", mode="mock"))
    await Worker(handlers={"judgment": handler}).process_job(tenant, await read_tx(tenant, job))
    saved = await get_judgment(tenant, created["request_id"], run_id)
    assert saved is not None
    assert json.loads(saved["judgment"]["rule_effects"])[0]["outcome"] == "out_of_scope"


async def test_learning_ids_are_tenant_scoped_and_schema_idempotent():
    await apply_schema()
    await apply_schema()
    tenants = [f"rule_scope_{uuid4().hex}" for _ in range(2)]
    try:
        for tenant in tenants:
            async def seed(tx, tenant=tenant):
                for label, identity in (("RuleCandidate", "cand_shared"),
                                        ("RuleVersion", "R-ROUTE-07@1")):
                    await (await tx.run(f"CREATE (n:{label} {{tenant_id:$tenant,id:$id}})",
                                        tenant=tenant, id=identity)).consume()
            await write_tx(tenant, seed)
        for tenant in tenants:
            async def count(tx, tenant=tenant):
                return (await (await tx.run("MATCH (r:RuleVersion {tenant_id:$tenant,id:'R-ROUTE-07@1'}) RETURN count(r) AS n", tenant=tenant)).single(strict=True))["n"]
            assert await read_tx(tenant, count) == 1
    finally:
        for tenant in tenants:
            async def cleanup(tx, tenant=tenant):
                await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=tenant)).consume()
            await write_tx(tenant, cleanup)


async def test_context_guidance_is_data_and_scope_bound(tenant):
    candidate = await seed_candidate(tenant, effect="context", context_text="검증된 운영 기준",
                                     scope={"all": [{"requester_org": "org_it"}]})
    version = await validated_version(tenant, candidate)
    await change_publication(tenant, "admin", "R-AI_NEED-01", "publish", version, 1, "게시", str(uuid4()))
    created = await create_request(tenant, "tester", "판단 요청입니다.", [], str(uuid4()), str(uuid4()),
                                   datetime.now(UTC).isoformat(), org_ids=["org_it"])
    run_id = (await get_request_meta(tenant, created["request_id"]))["active_run_id"]
    async def job(tx):
        return (await (await tx.run("MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id", tenant=tenant, run=run_id)).single(strict=True))["id"]
    states = []
    class RecordingClient:
        def __init__(self):
            self.inner = AiClient("", mode="mock")
        def ask(self, state, questions):
            states.append(state)
            return self.inner.ask(state, questions)
    async def handler(ctx):
        await execute_judgment(ctx, RecordingClient())
    await Worker(handlers={"judgment": handler}).process_job(tenant, await read_tx(tenant, job))
    saved = await get_judgment(tenant, created["request_id"], run_id)
    assert states and states[0]["operating_guidance"] == ["검증된 운영 기준"]
    assert saved is not None
    assert json.loads(saved["judgment"]["rule_effects"])[0]["effect"] == "context"


async def test_unsafe_rule_rejected_at_create_publish_and_revert(tenant):
    unsafe = await seed_candidate(tenant, target="feasibility", action={"set": "가능"})
    with pytest.raises(PolicyError) as decision_error:
        await decide_candidate(tenant, "admin", unsafe, "approve", None, "검토", str(uuid4()))
    assert decision_error.value.code == "RULE_INVARIANT"
    safe_for_creation = await seed_candidate(tenant)
    decision = await decide_candidate(tenant, "admin", safe_for_creation, "approve", None, "검토", str(uuid4()))
    async def corrupt_candidate(tx):
        body = proposed(safe_for_creation, target="feasibility", action={"set": "가능"})
        await (await tx.run("MATCH (c:RuleCandidate {tenant_id:$tenant,id:$id}) SET c.proposed_body=$body", tenant=tenant, id=safe_for_creation, body=json.dumps(body))).consume()
    await write_tx(tenant, corrupt_candidate)
    with pytest.raises(PolicyError) as create_error:
        await create_version(tenant, "admin", "R-FEASIBILITY-01", decision["decision_id"], {},
                             "생성", str(uuid4()))
    assert create_error.value.code == "RULE_INVARIANT"
    safe = await seed_candidate(tenant)
    version = await validated_version(tenant, safe)
    async def alter(tx):
        row = await (await tx.run("MATCH (r:RuleVersion {tenant_id:$tenant,id:$id}) RETURN r.body AS body", tenant=tenant, id=f"R-AI_NEED-01@{version}")).single(strict=True)
        body = json.loads(row["body"])
        body.update(target="feasibility", action={"set": "가능"})
        await (await tx.run("MATCH (r:RuleVersion {tenant_id:$tenant,id:$id}) SET r.body=$body", tenant=tenant, id=f"R-AI_NEED-01@{version}", body=json.dumps(body))).consume()
        return row["body"]
    original_body = await write_tx(tenant, alter)
    with pytest.raises(PolicyError):
        await change_publication(tenant, "admin", "R-AI_NEED-01", "publish", version, 1,
                                 "게시", str(uuid4()))
    async def restore(tx):
        await (await tx.run("MATCH (r:RuleVersion {tenant_id:$tenant,id:$id}) SET r.body=$body", tenant=tenant, id=f"R-AI_NEED-01@{version}", body=original_body)).consume()
    await write_tx(tenant, restore)
    await change_publication(tenant, "admin", "R-AI_NEED-01", "publish", version, 1, "게시", str(uuid4()))
    await change_publication(tenant, "admin", "R-AI_NEED-01", "stop", None, 2, "중단", str(uuid4()))
    await write_tx(tenant, alter)
    with pytest.raises(PolicyError):
        await change_publication(tenant, "admin", "R-AI_NEED-01", "revert", version, 3,
                                 "되돌리기", str(uuid4()))
    assert (await get_active_snapshot(tenant))[0] == 3
