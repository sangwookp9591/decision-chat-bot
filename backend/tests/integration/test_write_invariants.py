"""Regression tests for run creation and task start guards."""
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from jevtriage.auth.core import Principal
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.domain.runs import start_run_in_tx
from jevtriage.ingest.store import create_request
from jevtriage.jobs.worker import Worker
from jevtriage.judgment.jev_client import JevClient
from jevtriage.judgment.service import execute_judgment
from jevtriage.policy.service import bootstrap_policy
from jevtriage.review.store import get_review
from jevtriage.tasks.service import TaskError, transition


def test_product_run_writes_use_one_helper():
    root = Path(__file__).resolve().parents[2] / "jevtriage"
    # Legacy shadow validation and DB primitives do not create active judgment runs.
    exempt = {"learning/shadow.py", "db/requests.py", "db/jobs.py"}
    for path in root.rglob("*.py"):
        if path.name == "runs.py" or path.relative_to(root).as_posix() in exempt:
            continue
        source = path.read_text()
        assert "CREATE (run:Run" not in source, path
        assert "CREATE (job:Job" not in source, path
        assert "SET r.active_run_id" not in source, path
        assert "SET q.active_run_id" not in source, path
    for path in root.rglob("*.py"):
        if path.relative_to(root).as_posix() in exempt:
            continue
        source = path.read_text()
        assert "create_job(" not in source, path
        assert "set_active_run(" not in source, path


@pytest.mark.asyncio
async def test_unresolved_task_cannot_start():
    tenant = f"write_{uuid4().hex}"
    task_id = f"task_{uuid4().hex}"
    org = f"{tenant}-it"
    await apply_schema()

    async def seed(tx):
        await (await tx.run(
            "CREATE (o:Org {tenant_id:$tenant,id:$org}) "
            "CREATE (t:Task {tenant_id:$tenant,id:$task,status:'막힘',"
            "block_reasons:['feasibility_unresolved']}) "
            "CREATE (t)-[:ASSIGNED_TO {role:'lead'}]->(o)",
            tenant=tenant, org=org, task=task_id,
        )).consume()

    await write_tx(tenant, seed)
    principal = Principal(tenant, "worker", (org,), frozenset({"team_member"}))
    try:
        with pytest.raises(TaskError) as error:
            await transition(principal, task_id, "진행", "막힘")
        assert error.value.status_code == 409

        async def status(tx):
            row = await (await tx.run(
                "MATCH (t:Task {tenant_id:$tenant,id:$task}) RETURN t.status AS status",
                tenant=tenant, task=task_id,
            )).single(strict=True)
            return row["status"]

        assert await read_tx(tenant, status) == "막힘"
    finally:
        async def cleanup(tx):
            await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=tenant)).consume()
        await write_tx(tenant, cleanup)


@pytest.mark.asyncio
async def test_run_start_pins_config_and_rejects_stale_pointer():
    tenant = f"write_{uuid4().hex}"
    await apply_schema()
    await bootstrap_policy(tenant)
    try:
        created = await create_request(
            tenant, "requester", "판단할 업무", [], str(uuid4()), str(uuid4()),
            datetime.now(UTC).isoformat(),
        )
        request_id = created["request_id"]

        async def inspect(tx):
            return await (await tx.run(
                "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
                "MATCH (r:Run {tenant_id:$tenant,id:q.active_run_id}) "
                "MATCH (j:Job {tenant_id:$tenant,run_id:r.id}) "
                "RETURN q.latest_revision_id AS revision,r.id AS run,"
                "r.config_version AS version,r.versions_json AS versions,j.id AS job",
                tenant=tenant, request=request_id,
            )).single(strict=True)

        row = await read_tx(tenant, inspect)
        assert row["version"] == 1
        assert '"config_version": 1' in row["versions"]
        assert row["job"]

        async def stale(tx):
            await start_run_in_tx(tx, tenant, request_id, row["revision"], "reanalysis",
                                  expected_active_run_id="outdated")

        with pytest.raises(ValueError, match="stale_active_run"):
            await write_tx(tenant, stale)
        assert (await read_tx(tenant, inspect))["run"] == row["run"]
    finally:
        async def cleanup(tx):
            await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=tenant)).consume()
        await write_tx(tenant, cleanup)


@pytest.mark.asyncio
async def test_judgment_keeps_evaluated_eligibility():
    tenant = f"write_{uuid4().hex}"
    await apply_schema()
    try:
        created = await create_request(
            tenant, "requester", "일반 업무 판단 요청", [], str(uuid4()), str(uuid4()),
            datetime.now(UTC).isoformat(),
        )

        async def job(tx):
            return (await (await tx.run(
                "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
                "MATCH (j:Job {tenant_id:$tenant,run_id:q.active_run_id}) "
                "RETURN j.id AS id",
                tenant=tenant, request=created["request_id"],
            )).single(strict=True))["id"]

        async def handler(ctx):
            await execute_judgment(ctx, JevClient("", mode="mock"))

        await Worker(handlers={"judgment": handler}).process_job(tenant, await read_tx(tenant, job))

        async def eligibility(tx):
            return await (await tx.run(
                "MATCH (j:Judgment {tenant_id:$tenant,request_id:$request}) "
                "RETURN j.eligibility_json AS eligibility,j.versions AS versions",
                tenant=tenant, request=created["request_id"],
            )).single(strict=True)

        row = await read_tx(tenant, eligibility)
        assert isinstance(json.loads(row["eligibility"])["allowed"], bool)
        assert "reasons" in json.loads(row["eligibility"])
        assert json.loads(row["versions"])["config_version"] == 0
    finally:
        async def cleanup(tx):
            await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=tenant)).consume()
        await write_tx(tenant, cleanup)


@pytest.mark.asyncio
async def test_review_history_does_not_follow_cross_tenant_correction():
    tenant = f"write_{uuid4().hex}"
    foreign = f"foreign_{uuid4().hex}"
    review_id = f"review_{uuid4().hex}"
    await apply_schema()
    try:
        async def seed(tx):
            await (await tx.run(
                "CREATE (q:Request {tenant_id:$tenant,id:$request}) "
                "CREATE (v:Review {tenant_id:$tenant,id:$review,request_id:$request,run_id:$run}) "
                "CREATE (h:ReviewDecision {tenant_id:$tenant,id:$decision}) "
                "CREATE (c:Correction {tenant_id:$foreign,id:$correction,reason:'foreign'}) "
                "CREATE (v)-[:HAS_DECISION]->(h) CREATE (h)-[:RECORDED]->(c)",
                tenant=tenant, foreign=foreign, request=f"req_{uuid4().hex}",
                review=review_id, run=f"run_{uuid4().hex}",
                decision=f"decision_{uuid4().hex}", correction=f"correction_{uuid4().hex}",
            )).consume()

        await write_tx(tenant, seed)
        review = await get_review(tenant, review_id)
        assert len(review["history"]) == 1
        assert review["history"][0]["corrections"] == []
    finally:
        async def cleanup(tx):
            await (await tx.run(
                "MATCH (n) WHERE n.tenant_id IN [$tenant,$foreign] DETACH DELETE n",
                tenant=tenant, foreign=foreign,
            )).consume()
        await write_tx(tenant, cleanup)
