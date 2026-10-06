"""Safety allowlist and insufficient-evidence approval contracts."""
import json
from uuid import uuid4

import httpx
import pytest

from ildongi.auth.core import Principal, enforce_csrf, get_principal
from ildongi.db.schema import apply_schema
from ildongi.db.tx import read_tx, write_tx
from ildongi.learning.apply import apply_rules, validate_rule
from ildongi.main import create_app
from ildongi.policy.service import DEFAULT_CONFIG, get_active_snapshot, validate_config

pytestmark = pytest.mark.asyncio(loop_scope="session")


def rule(target, action):
    return {"schema": "rule-v1", "rule_id": "R-SAFETY-01", "version": 1,
            "effect": "rule", "target": target, "scope": {"all": []}, "action": action}


async def test_target_action_allowlist_and_config_code():
    for body in (rule("urgency", {"set": "판단 보류"}),
                 rule("urgency", {"set": "일반"}),
                 rule("feasibility", {"set": "가능"}),
                 rule("lead_org", {"set": "외부"}),
                 rule("collab_orgs", {"add": "외부"}),
                 rule("review_route", {"set": "skip"}),
                 rule("risk_confirmed", {"set": True})):
        with pytest.raises(ValueError):
            validate_rule(body)
        _, errors = validate_config({**DEFAULT_CONFIG, "rules": [{k: v for k, v in body.items() if k != "schema"}]})
        assert errors[0]["code"] == "RULE_INVARIANT"
    for body in (rule("urgency", {"set": "긴급"}),
                 rule("urgency", {"require_review": "추가 검토"}),
                 rule("feasibility", {"set": "정보 부족"}),
                 rule("review_route", {"require_review": "추가 검토"})):
        validate_rule(body)


async def test_legacy_unsafe_rule_is_recorded_and_not_applied():
    original = {"classifications": {"urgency": "긴급", "feasibility": "조건부 가능", "ai_need": "필요", "lead_org": "AI팀"},
                "risk": {"confirmed": False}, "review_reasons": ["필수 검토"]}
    result, applications = apply_rules(original, [rule("urgency", {"set": "판단 보류"}),
                                                rule("feasibility", {"set": "가능"})])
    assert result["classifications"] == original["classifications"]
    assert [a["outcome"] for a in applications] == ["blocked_by_invariant"] * 2
    assert result["review_reasons"] == ["필수 검토"]


async def test_legacy_rule_in_active_config_is_blocked():
    tenant = f"legacy_rule_{uuid4().hex}"
    unsafe = rule("urgency", {"set": "판단 보류"})
    async def seed(tx):
        await (await tx.run("CREATE (:ConfigVersion {tenant_id:$tenant,id:$id,version:1,status:'active',config_json:$config})",
                            tenant=tenant, id=f"cfg_{tenant}_1",
                            config=json.dumps({**DEFAULT_CONFIG, "rules": [{k: v for k, v in unsafe.items() if k != "schema"}]}))).consume()
    await write_tx(tenant, seed)
    try:
        _, snapshot = await get_active_snapshot(tenant)
        original = {"classifications": {"urgency": "긴급"}, "risk": {"confirmed": False}, "review_reasons": ["긴급 필수 검토"]}
        result, applications = apply_rules(original, snapshot["rules"])
        assert result["classifications"]["urgency"] == "긴급"
        assert applications[0]["outcome"] == "blocked_by_invariant"
    finally:
        async def cleanup(tx):
            await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=tenant)).consume()
        await write_tx(tenant, cleanup)


async def test_insufficient_candidate_requires_explicit_ack_at_both_steps():
    tenant = f"invariant_{uuid4().hex}"
    await apply_schema()
    async def seed(tx):
        proposed = rule("ai_need", {"set": "혼합"})
        await (await tx.run("CREATE (:RuleCandidate {tenant_id:$tenant,id:'cand_insufficient',status:'자료 부족',proposed_body:$body})",
                            tenant=tenant, body=json.dumps(proposed))).consume()
    await write_tx(tenant, seed)
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal(tenant, "admin", (), frozenset({"rule_admin"}))
    app.dependency_overrides[enforce_csrf] = lambda: None
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            url = "/api/learning/candidates/cand_insufficient/decision"
            headers = {"Idempotency-Key": str(uuid4())}
            body = {"action": "approve", "reason": "근거 부족을 인지하고 제한적 검증을 진행합니다"}
            assert (await client.post(url, headers=headers, json=body)).status_code == 422
            approved = await client.post(url, headers={"Idempotency-Key": str(uuid4())},
                                         json={**body, "acknowledge_insufficient": True})
            assert approved.status_code == 200 and approved.json()["insufficient_approval_label"] == "자료 부족 상태로 승인됨"
            version_url = "/api/learning/rules/R-SAFETY-01/versions"
            version_body = {"decision_id": approved.json()["decision_id"], "reason": body["reason"]}
            assert (await client.post(version_url, headers={"Idempotency-Key": str(uuid4())}, json=version_body)).status_code == 422
            created = await client.post(version_url, headers={"Idempotency-Key": str(uuid4())},
                                        json={**version_body, "acknowledge_insufficient": True})
            assert created.status_code == 200 and created.json()["insufficient_approved"] is True
        async def persisted(tx):
            return await (await tx.run("MATCH (d:RuleDecision {tenant_id:$tenant}) RETURN d.insufficient_approved AS approved,d.reason AS reason", tenant=tenant)).single(strict=True)
        assert (await read_tx(tenant, persisted))["approved"] is True
    finally:
        async def cleanup(tx):
            await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=tenant)).consume()
        await write_tx(tenant, cleanup)
