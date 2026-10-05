"""Persisted source evidence keeps its real creation metadata in Neo4j and graph detail."""
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

from jevtriage.auth.core import Principal, get_principal
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.ingest.store import create_request
from jevtriage.main import create_app


@pytest.mark.asyncio(loop_scope="session")
async def test_ingested_evidence_creation_time_and_creator_reach_graph_detail():
    tenant = f"evidence_metadata_{uuid4().hex}"
    user_id = "evidence-author"
    await apply_schema()

    async def cleanup(tx):
        await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=tenant)).consume()

    try:
        await create_request(
            tenant, user_id, "시설 점검 입력과 확인 요청입니다.", [],
            "evidence-metadata-key", "evidence-metadata-hash", datetime.now(UTC).isoformat(),
        )

        async def get_evidence(tx):
            row = await (await tx.run(
                "MATCH (e:EvidenceSpan {tenant_id:$tenant}) RETURN e.id AS id, "
                "e.created_at AS created_at, e.created_by AS created_by LIMIT 1",
                tenant=tenant,
            )).single(strict=True)
            return row

        stored = await read_tx(tenant, get_evidence)
        assert stored["created_at"] is not None, "evidence creation time must be persisted"
        assert stored["created_by"] == user_id

        app = create_app()
        app.dependency_overrides[get_principal] = lambda: Principal(
            tenant, user_id, (), frozenset({"operator"}), can_read_source=True,
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://evidence-metadata",
        ) as client:
            response = await client.get(f"/api/graph/judgment/nodes/{stored['id']}")
        assert response.status_code == 200
        detail = response.json()
        assert detail["at"] is not None
        assert detail["actor"] == user_id
    finally:
        await write_tx(tenant, cleanup)
