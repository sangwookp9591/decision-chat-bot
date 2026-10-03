"""Human rule-candidate proposal API (found by the T38 scenario: any(<async generator>) made it return 500)."""
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from jevtriage.auth.core import Principal, get_principal
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import write_tx
from jevtriage.main import create_app
from jevtriage.policy.service import bootstrap_policy
from tests.integration.test_candidates import seed_corrections

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
async def tenant():
    value = f"candprop_{uuid4().hex}"
    await apply_schema()
    await bootstrap_policy(value)
    yield value

    async def cleanup(tx):
        await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=value)).consume()
    await write_tx(value, cleanup)


async def test_human_proposal_with_and_without_support_and_valid_rule_id(tenant):
    await seed_corrections(tenant, 1)
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal(tenant, "user", (), frozenset({"rule_admin"}), False)
    with TestClient(app) as client:
        correction = client.get("/api/learning/corrections?field=feasibility").json()["corrections"][0]["id"]
        body = {"field": "feasibility", "proposed_action": {"set": "현재 불가"}, "scope": {"all": []}, "rationale": "T38 regression"}
        without = client.post("/api/learning/candidates", json={**body, "supporting_correction_ids": []})
        with_support = client.post("/api/learning/candidates", json={**body, "supporting_correction_ids": [correction]})
        missing = client.post("/api/learning/candidates", json={**body, "supporting_correction_ids": ["cor_missing"]})
    assert without.status_code == 201 and with_support.status_code == 201
    assert missing.status_code == 404
    assert with_support.json()["status"] == "자료 부족"  # one support < minimum 3
    # The proposed rule id must satisfy the server's rule id format (underscores, no extra hyphen).
    import re
    assert re.fullmatch(r"R-[A-Z_]+-[0-9]{2,}", with_support.json()["proposed_body"]["rule_id"])
