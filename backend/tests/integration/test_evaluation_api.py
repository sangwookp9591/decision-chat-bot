from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from jevtriage.auth.core import Principal, enforce_csrf, get_principal
from jevtriage.db.driver import get_driver
from jevtriage.main import create_app

pytestmark = pytest.mark.asyncio(loop_scope="session")
FIELDS = {"ai_need": "필요", "feasibility": "가능", "urgency": "일반", "team_set": ["AI팀"], "risk_areas": []}


async def test_label_edit_defer_resume_disagreement_and_consensus():
    from jevtriage.evaluation.service import _rows
    tenant = f"eval_{uuid4().hex}"
    sample = _rows("tuning")[0]["id"]
    app = create_app()
    app.dependency_overrides[enforce_csrf] = lambda: None

    def client(user, role):
        app.dependency_overrides[get_principal] = lambda: Principal(tenant, user, (), frozenset({role}))
        return TestClient(app)

    def put(user, role, body):
        with client(user, role) as http:
            return http.put(f"/api/evaluation/candidates/tuning/{sample}", json=body)

    try:
        denied = put("nope", "requester", {"labels": FIELDS, "confidence": .8})
        assert denied.status_code == 403
        body = {"labels": {**FIELDS, "ai_need": "불필요"}, "confidence": .7}
        assert put("one", "labeler", {**body, "status": "deferred", "reason": "근거 부족"}).status_code == 200
        assert put("one", "labeler", body).status_code == 200  # resume after defer, with an edited value
        assert put("two", "reviewer", {"labels": FIELDS, "confidence": .9}).status_code == 200
        with client("one", "labeler") as http:
            final_items = http.get("/api/evaluation/candidates?split=final").json()["candidates"]
            assert final_items and "proposed_labels" not in final_items[0] and "rationale" not in final_items[0]
            items = http.get("/api/evaluation/candidates?split=tuning").json()["candidates"]
            item = next(row for row in items if row["id"] == sample)
            assert item["consensus"] == "consensus_required"
            assert len(item["labels"]) == 2
            before = http.get("/api/evaluation/candidates?split=tuning").json()["progress"]["confirmed"]
            resolved = http.post(f"/api/evaluation/candidates/tuning/{sample}/consensus", json={"labels": FIELDS, "confidence": .95})
            assert resolved.status_code == 200
            after_data = http.get("/api/evaluation/candidates?split=tuning").json()
            assert after_data["progress"]["confirmed"] >= before
            item = next(row for row in after_data["candidates"] if row["id"] == sample)
            assert item["consensus"] == "resolved"
            assert item["my_labels"]["labels"]["team_set"] == ["AI팀"]
        driver = await get_driver()
        async with driver.session() as session:
            audit = await (await session.run("MATCH (a:AuditEvent {tenant_id:$tenant,kind:'evaluation_label',subject:$id}) RETURN count(a) AS count", tenant=tenant, id=sample)).single(strict=True)
            assert audit["count"] == 4
    finally:
        driver = await get_driver()
        async with driver.session() as session:
            await (await session.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=tenant)).consume()
        app.dependency_overrides.clear()


async def test_invalid_label_returns_field_specific_422():
    from jevtriage.evaluation.service import _rows

    tenant = f"eval_{uuid4().hex}"
    sample = _rows("tuning")[0]["id"]
    app = create_app()
    app.dependency_overrides[enforce_csrf] = lambda: None
    app.dependency_overrides[get_principal] = lambda: Principal(tenant, "labeler", (), frozenset({"labeler"}))
    try:
        with TestClient(app) as http:
            response = http.put(f"/api/evaluation/candidates/tuning/{sample}", json={
                "labels": {**FIELDS, "team_set": "AI팀"}, "confidence": .8,
            })
        assert response.status_code == 422
        assert response.json()["detail"]["details"]["fields"]["team_set"]
    finally:
        app.dependency_overrides.clear()
