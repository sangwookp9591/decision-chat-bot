"""Real Neo4j candidate, shadow, publication and request/review API flow."""
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from ildongi.auth.core import Principal, enforce_csrf, get_principal
from ildongi.db.schema import apply_schema
from ildongi.db.tx import read_tx, write_tx
from ildongi.ingest.store import create_request, get_request_meta
from ildongi.jobs.worker import Worker
from ildongi.judgment.ai_client import AiClient
from ildongi.judgment.service import execute_judgment
from ildongi.judgment.store import get_judgment
from ildongi.learning.rules import (
    change_publication,
    create_version,
    decide_candidate,
    mark_validated,
)
from ildongi.learning.shadow import validate_rules
from ildongi.main import create_app
from ildongi.policy.service import PolicyError, bootstrap_policy

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def tenant():
    value = f"keyword_{uuid4().hex}"
    await apply_schema()
    await bootstrap_policy(value)
    async def seed(tx):
        await (await tx.run("CREATE (:Org {tenant_id:$tenant,id:$id,name:'it'})",
                            tenant=value, id=f"{value}-it")).consume()
    await write_tx(value, seed)
    yield value
    async def cleanup(tx):
        await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=value)).consume()
    await write_tx(value, cleanup)


def app_for(tenant, role="rule_admin", source=True):
    app = create_app()
    app.dependency_overrides[enforce_csrf] = lambda: None
    app.dependency_overrides[get_principal] = lambda: Principal(
        tenant, "tester", (f"{tenant}-it",), frozenset({role}), can_read_source=source)
    return app


async def request_and_run(tenant, text="VPN 접속이 안 됩니다"):
    created = await create_request(tenant, "tester", text, [], str(uuid4()), str(uuid4()),
                                   datetime.now(UTC).isoformat(), org_ids=[f"{tenant}-it"])
    run_id = (await get_request_meta(tenant, created["request_id"]))["active_run_id"]
    async def job(tx):
        return (await (await tx.run("MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id",
                                    tenant=tenant, run=run_id)).single(strict=True))["id"]
    errors = []
    async def handler(ctx):
        try:
            await execute_judgment(ctx, AiClient("", mode="mock"))
        except Exception as exc:
            errors.append(repr(exc))
            raise
    await Worker(handlers={"judgment": handler}).process_job(tenant, await read_tx(tenant, job))
    saved = await get_judgment(tenant, created["request_id"], run_id)
    assert saved is not None, errors
    return created["request_id"], run_id, saved


async def test_org_permissions_and_candidate_scope_validation(tenant):
    for role in ("reviewer", "rule_admin", "operator", "requester", "policy_editor"):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_for(tenant, role)), base_url="http://test") as client:
            response = await client.get("/api/learning/orgs")
            assert response.status_code == (200 if role in {"reviewer", "rule_admin", "operator"} else 403)
            if response.status_code == 200:
                assert response.json()["orgs"] == [{"id": f"{tenant}-it", "name": "it"}]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_for(tenant)), base_url="http://test") as client:
        body = {"field": "lead_org", "proposed_action": {"set": "IT팀"},
                "scope": {"all": [{"text": {"contains_any": ["VPN"]}}, {"requester_org": f"{tenant}-it"}]},
                "rationale": "VPN 요청 운영 규칙", "supporting_correction_ids": []}
        response = await client.post("/api/learning/candidates", json=body)
        assert response.status_code == 201, response.text
        candidate_id = response.json()["id"]
        for org in ("IT팀", "other-tenant-it"):
            invalid = {**body, "scope": {"all": [{"requester_org": org}]}}
            response = await client.post("/api/learning/candidates", json=invalid)
            assert response.status_code == 422 and response.json()["detail"]["code"] == "UNKNOWN_ORG"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_for(tenant, source=False)), base_url="http://test") as client:
        response = await client.get(f"/api/learning/candidates/{candidate_id}")
        assert response.status_code == 200
        assert response.json()["proposed_body"]["scope"] == body["scope"]
    with pytest.raises(PolicyError) as error:
        await decide_candidate(tenant, "tester", candidate_id, "approve_with_scope_change",
                               {"all": [{"requester_org": "IT팀"}]}, "범위 수정 승인 사유입니다", str(uuid4()), True)
    assert error.value.code == "UNKNOWN_ORG"


async def test_shadow_publish_execution_and_decoded_apis(tenant):
    request_id, _, saved = await request_and_run(tenant)
    # Preserve an observable baseline which differs from the keyword rule.
    async def baseline(tx):
        await (await tx.run("MATCH (j:Judgment {tenant_id:$tenant,id:$id}) SET j.lead_org='AI팀'",
                            tenant=tenant, id=saved["judgment"]["id"])).consume()
    await write_tx(tenant, baseline)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_for(tenant)), base_url="http://test") as client:
        response = await client.post("/api/learning/candidates", json={
            "field": "lead_org", "proposed_action": {"set": "IT팀"},
            "scope": {"all": [{"text": {"contains_any": ["VPN"]}}]},
            "rationale": "VPN 접속 요청을 IT팀으로 분류합니다", "supporting_correction_ids": []})
        assert response.status_code == 201, response.text
        candidate = response.json()["id"]
    decision = await decide_candidate(tenant, "tester", candidate, "approve", None,
                                      "자료 부족을 인정하고 검증용 승인합니다", str(uuid4()), True)
    version = await create_version(tenant, "tester", "R-LEAD_ORG-03", decision["decision_id"], {},
                                   "키워드 규칙 버전 생성", str(uuid4()), True)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_for(tenant, source=False)), base_url="http://test") as client:
        response = await client.get("/api/learning/rules/R-LEAD_ORG-03")
        assert response.status_code == 200
        assert response.json()["versions"][0]["body"]["scope"] == {"all": [{"text": {"contains_any": ["VPN"]}}]}
    validation = await validate_rules(tenant, "tester", "R-LEAD_ORG-03", version["version"],
                                      datetime.now(UTC) - timedelta(days=1), datetime.now(UTC) + timedelta(days=1),
                                      scope_filter=request_id)
    assert validation["changed_count"] == 1 and validation["status"] == "completed", validation
    assert validation["side_effects"] == validation["calls"] == 0
    await mark_validated(tenant, "tester", "R-LEAD_ORG-03", version["version"], validation["id"], "부작용 없음", str(uuid4()))
    await change_publication(tenant, "tester", "R-LEAD_ORG-03", "publish", version["version"], 1, "규칙 게시", str(uuid4()))
    request_id, run_id, saved = await request_and_run(tenant)
    effects = json.loads(saved["judgment"]["rule_effects"])
    assert saved["judgment"]["lead_org"] == "IT팀" and effects[0]["outcome"] == "used"
    assert effects[0]["matches"] and effects[0]["matches"][0]["keyword"] == "VPN"
    async def applied_source(tx):
        return (await (await tx.run(
            "MATCH (:RunStep {tenant_id:$tenant,run_id:$run})-[a:APPLIED]->"
            "(:RuleVersion {tenant_id:$tenant,id:'R-LEAD_ORG-03@1'}) RETURN a.source AS source",
            tenant=tenant, run=run_id,
        )).single(strict=True))["source"]
    assert await read_tx(tenant, applied_source) == effects[0]["source"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_for(tenant, "requester")), base_url="http://test") as client:
        response = await client.get(f"/api/requests/{request_id}/judgment")
        assert response.status_code == 200 and response.json()["rule_effects"] == effects
    async def review(tx):
        return (await (await tx.run("MATCH (r:Review {tenant_id:$tenant,run_id:$run}) RETURN r.id AS id",
                                    tenant=tenant, run=run_id)).single(strict=True))["id"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_for(tenant, "reviewer")), base_url="http://test") as client:
        response = await client.get(f"/api/reviews/{await read_tx(tenant, review)}")
        assert response.status_code == 200, response.text
        assert response.json()["judgment"]["rule_effects"] == effects
    # Removing text from a newer version must still load input for the published baseline.
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_for(tenant)), base_url="http://test") as client:
        response = await client.post("/api/learning/candidates", json={
            "field": "lead_org", "proposed_action": {"set": "AI팀"}, "scope": {"all": []},
            "rationale": "새 버전은 키워드 범위를 제거합니다", "supporting_correction_ids": []})
        assert response.status_code == 201
    newer_decision = await decide_candidate(tenant, "tester", response.json()["id"], "approve", None,
                                            "자료 부족을 인정하고 새 버전을 검증합니다", str(uuid4()), True)
    newer = await create_version(tenant, "tester", "R-LEAD_ORG-03", newer_decision["decision_id"], {},
                                 "키워드 범위 제거 검증", str(uuid4()), True)
    async def reset_model_value(tx):
        await (await tx.run("MATCH (j:Judgment {tenant_id:$tenant,request_id:$request}) SET j.lead_org='AI팀'",
                            tenant=tenant, request=request_id)).consume()
    await write_tx(tenant, reset_model_value)
    comparison = await validate_rules(tenant, "tester", "R-LEAD_ORG-03", newer["version"],
                                      datetime.now(UTC) - timedelta(days=1), datetime.now(UTC) + timedelta(days=1),
                                      scope_filter=request_id)
    assert comparison["changed_count"] == 1 and comparison["status"] == "completed", comparison
    # A missing revision is recorded as input_unavailable, never silently zero changes.
    async def remove_input(tx):
        await (await tx.run("MATCH (j:Judgment {tenant_id:$tenant,request_id:$request}) SET j.revision_id='missing'",
                            tenant=tenant, request=request_id)).consume()
    await write_tx(tenant, remove_input)
    validation = await validate_rules(tenant, "tester", "R-LEAD_ORG-03", version["version"],
                                      datetime.now(UTC) - timedelta(days=1), datetime.now(UTC) + timedelta(days=1),
                                      scope_filter=request_id)
    assert validation["status"] == "failed" and validation["failures"][0]["reason"] == "input_unavailable"
