"""Seed and remove an isolated review-display E2E tenant on shared Neo4j."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "backend/tests/acceptance"), str(ROOT / "backend/tests/integration")]
from provision import provision  # noqa: E402
from test_review_assignment import sample  # noqa: E402
from jevtriage.db.driver import close_driver  # noqa: E402
from jevtriage.db.tx import write_tx  # noqa: E402


async def main(tenant: str, clear: bool = False) -> None:
    if clear:
        async def remove(tx):
            await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=tenant)).consume()
        await write_tx(tenant, remove)
        return
    await provision((tenant,))
    _principal, _review_id, command = await sample(tenant)
    async def annotate(tx):
        await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
            "SET q.title='회의실 예약 자동화',q.preview='회의실 예약 자동화를 요청합니다. 상세 정보는 권한에 따라 표시됩니다.',"
            "q.org_ids=[$org],q.created_by=$requester",
            tenant=tenant, request=command["request_id"], org=f"{tenant}-ai",
            requester=f"usr_{tenant}_requester",
        )).consume()
        await (await tx.run(
            "MATCH (u:User {tenant_id:$tenant,id:$reviewer}) SET u.can_read_source=false "
            "WITH u MATCH (o:Org {tenant_id:$tenant,id:$it}) "
            "CREATE (u)-[:MEMBER_OF {role:'reviewer'}]->(o) "
            "WITH u MATCH (reader:User {tenant_id:$tenant,id:$source_reader}) SET reader.can_read_source=true "
            "WITH reader MATCH (o:Org {tenant_id:$tenant,id:$it}) "
            "CREATE (reader)-[:MEMBER_OF {role:'reviewer'}]->(o) "
            "WITH reader MATCH (requester:User {tenant_id:$tenant,id:$requester}) SET requester.can_read_source=true",
            tenant=tenant, reviewer=f"usr_{tenant}_reviewer", source_reader=f"usr_{tenant}_source_reader",
            requester=f"usr_{tenant}_requester", it=f"{tenant}-it",
        )).consume()
    await write_tx(tenant, annotate)
    print(json.dumps({"tenant": tenant, "request_id": command["request_id"]}))


try:
    asyncio.run(main(sys.argv[1], len(sys.argv) > 2 and sys.argv[2] == "clear"))
finally:
    asyncio.run(close_driver())
