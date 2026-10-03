"""Persisted execution projections against the integration Neo4j database."""

from uuid import uuid4

import pytest

from jevtriage.db.requests import add_input_revision, create_request
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.observe.flow import get_flow
from jevtriage.observe.playback import get_playback
from jevtriage.observe.topology import get_topology

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_observe_reads_saved_steps_reviews_and_real_topology():
    tenant = f"t17_{uuid4().hex}"
    await apply_schema()
    request_id = await create_request(tenant, "tester")
    revision_id, _ = await add_input_revision(tenant, request_id, "tester")
    run_id = f"run_{uuid4().hex}"
    step_a, step_b, review_id = (f"step_{uuid4().hex}" for _ in range(3))

    async def seed(tx):
        await (await tx.run(
            "CREATE (:Run {id:$run,tenant_id:$tenant,request_id:$request,input_revision_id:$revision,status:'succeeded',config_version:4})",
            run=run_id, tenant=tenant, request=request_id, revision=revision_id,
        )).consume()
        await (await tx.run(
            "MATCH (r:Run {id:$run,tenant_id:$tenant}) "
            "CREATE (r)-[:HAS_STEP]->(:RunStep {id:$a,tenant_id:$tenant,run_id:$run,name:'extract',kind:'code',actor:'code',status:'succeeded',started_at:datetime('2026-01-01T00:00:00Z'),ended_at:datetime('2026-01-01T00:00:01Z'),duration_ms:1000,versions_json:'{}',input_summary_json:'{}',output_summary_json:'{}',attempt_id:'att_a'}) "
            "CREATE (r)-[:HAS_STEP]->(:RunStep {id:$b,tenant_id:$tenant,run_id:$run,name:'judge',kind:'ai',actor:'ai',status:'skipped',started_at:datetime('2026-01-01T00:00:01Z'),versions_json:'{}',predecessor_ids:[$a],attempt_id:'att_b'}) "
            "CREATE (v:Review {id:$review,tenant_id:$tenant,request_id:$request,run_id:$run,status:'approved',created_at:datetime('2026-01-01T00:00:02Z')}) "
            "CREATE (d:ReviewDecision {id:$decision,tenant_id:$tenant,review_id:$review,action:'approve_with_changes',actor_id:'reviewer_1',created_at:datetime('2026-01-01T00:00:07Z')}) "
            "CREATE (v)-[:HAS_DECISION]->(d) "
            "CREATE (:Review {id:$review2,tenant_id:$tenant,request_id:$request,run_id:$run,status:'pending',created_at:datetime('2026-01-01T00:00:08Z')})",
            run=run_id, tenant=tenant, request=request_id, a=step_a, b=step_b, review=review_id, decision=f"rdec_{uuid4().hex}", review2=f"rvw_{uuid4().hex}",
        )).consume()
        await (await tx.run("CREATE (:Task {id:'task_real',tenant_id:$tenant,title:'real'})",tenant=tenant)).consume()
        await (await tx.run("MATCH (q:Request {id:$request,tenant_id:$tenant}),(t:Task {id:'task_real',tenant_id:$tenant}) CREATE (q)-[:HAS_TASK]->(t)",request=request_id,tenant=tenant)).consume()

    await write_tx(tenant, seed)
    try:
        flow = await get_flow(tenant, run_id)
        assert {n["id"] for n in flow["nodes"]} >= {step_a, step_b, f"review:{review_id}"}
        person = next(n for n in flow["nodes"] if n["id"] == f"review:{review_id}")
        assert person["reviewer_id"] == "reviewer_1" and person["ended_at"] is not None
        assert isinstance(person["started_at"], str) and isinstance(person["ended_at"], str)
        assert all(isinstance(n.get("started_at"), str) for n in flow["nodes"] if n.get("started_at"))
        assert {e["from"] for e in flow["edges"]} == {step_a}
        async def counts(tx):
            labels = ["Judgment", "ModelOutput", "Job", "Assignment", "Task", "Event", "Review"]
            result = {}
            for label in labels:
                row = await (await tx.run(f"MATCH (n:{label} {{tenant_id:$tenant}}) RETURN count(n) AS n", tenant=tenant)).single()
                result[label] = row["n"]
            return result
        before = await read_tx(tenant, counts)
        playback = await get_playback(tenant, run_id)
        after = await read_tx(tenant, counts)
        assert before == after
        assert [e["type"] for e in playback["events"]].count("step_started") == 2
        assert all(isinstance(e["at"], str) for e in playback["events"] if e.get("at"))
        assert any(e["type"] == "human_wait_started" for e in playback["events"])
        business = await get_topology(tenant, request_id, "business")
        assert {n["id"] for n in business["nodes"]} == {request_id, "task_real"}
        async def cleanup(tx):
            await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n",tenant=tenant)).consume()
        await write_tx(tenant, cleanup)
    finally:
        async def cleanup(tx):
            await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n",tenant=tenant)).consume()
        await write_tx(tenant, cleanup)
