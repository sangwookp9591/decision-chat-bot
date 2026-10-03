"""Reanalysis result boundaries against Neo4j and one mock Jev worker pass."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio

from jevtriage.auth.core import Principal
from jevtriage.db.events import list_events
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.ingest.service import reanalyze
from jevtriage.ingest.store import create_request, get_request_meta
from jevtriage.jobs.worker import Worker
from jevtriage.judgment.jev_client import JevClient
from jevtriage.judgment.service import execute_judgment
from jevtriage.judgment.store import get_judgment
from jevtriage.review.service import ReviewError, decide

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture
async def tenant():
    value = f"fixr_{uuid4().hex}"
    await apply_schema()
    yield value
    async def cleanup(tx):
        await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=value)).consume()
    await write_tx(value, cleanup)


async def new_request(tenant):
    created = await create_request(tenant, "requester", "업무 요청입니다.", [],
                                   str(uuid4()), str(uuid4()), datetime.now(UTC).isoformat())
    return created["request_id"]


async def run_worker(tenant, run_id):
    async def job(tx):
        row = await (await tx.run(
            "MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id",
            tenant=tenant, run=run_id,
        )).single(strict=True)
        return row["id"]
    async def handler(ctx):
        await execute_judgment(ctx, JevClient("", mode="mock"))
    await Worker(handlers={"judgment": handler}).process_job(tenant, await read_tx(tenant, job))


async def snapshot(tenant, request_id):
    async def op(tx):
        row = await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
            "OPTIONAL MATCH (a:Assignment {tenant_id:$tenant,request_id:$request}) "
            "OPTIONAL MATCH (t:Task {tenant_id:$tenant,request_id:$request}) "
            "RETURN q.status AS status,q.assignment_id AS assignment_id,"
            "q.latest_judgment_id AS latest_judgment_id,"
            "collect(DISTINCT a.id) AS assignments,collect(DISTINCT {id:t.id,status:t.status}) AS tasks",
            tenant=tenant, request=request_id,
        )).single(strict=True)
        reviews = await (await tx.run(
            "MATCH (v:Review {tenant_id:$tenant,request_id:$request}) "
            "RETURN v.id AS id,v.run_id AS run_id,v.status AS status,"
            "v.reason AS reason,v.superseded_by AS superseded_by ORDER BY v.created_at,v.id",
            tenant=tenant, request=request_id,
        )).data()
        return {**dict(row), "reviews": reviews}
    return await read_tx(tenant, op)


async def start_again(tenant, request_id):
    principal = Principal(tenant, "requester", (), frozenset({"requester"}), True)
    return await reanalyze(principal, request_id, 1, "compare", str(uuid4()))


async def test_assigned_reanalysis_is_comparison_only(tenant):
    request_id = await new_request(tenant)
    initial_run = (await get_request_meta(tenant, request_id))["active_run_id"]
    await run_worker(tenant, initial_run)
    original = await get_judgment(tenant, request_id, initial_run)
    async def assigned(tx):
        await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
            "CREATE (a:Assignment {id:$assignment,tenant_id:$tenant,request_id:$request}) "
            "CREATE (t:Task {id:$task,tenant_id:$tenant,request_id:$request,status:'진행 중'}) "
            "SET q.assignment_id=$assignment,q.status='배정 완료'",
            tenant=tenant, request=request_id,
            assignment=f"as_{uuid4().hex}", task=f"task_{uuid4().hex}",
        )).consume()
    await write_tx(tenant, assigned)
    before = await snapshot(tenant, request_id)
    next_run = (await start_again(tenant, request_id))["run_id"]
    await run_worker(tenant, next_run)
    after = await snapshot(tenant, request_id)
    assert after == before
    compared = await get_judgment(tenant, request_id, next_run)
    assert compared["judgment"]["id"] != original["judgment"]["id"]
    assert compared["review"] is None
    kinds = [e["kind"] for e in await list_events(tenant) if e["run_id"] == next_run]
    assert "reanalysis.compared" in kinds
    assert "judgment_saved" not in kinds
    assert "assignment_created" not in kinds


async def test_pending_review_superseded_and_old_approval_conflicts(tenant):
    request_id = await new_request(tenant)
    old_run = (await get_request_meta(tenant, request_id))["active_run_id"]
    await run_worker(tenant, old_run)
    old_review = (await get_judgment(tenant, request_id, old_run))["review"]
    new_run = (await start_again(tenant, request_id))["run_id"]
    await run_worker(tenant, new_run)
    reviews = (await snapshot(tenant, request_id))["reviews"]
    assert len([v for v in reviews if v["status"] == "pending"]) == 1
    assert len([v for v in reviews if v["run_id"] == new_run]) == 1
    previous = next(v for v in reviews if v["id"] == old_review["id"])
    assert (previous["status"], previous["reason"], previous["superseded_by"]) == (
        "superseded", "newer_run", new_run)
    principal = Principal(tenant, "reviewer", ("org-review",), frozenset({"reviewer"}), True)
    command = {"action": "approve", "request_id": request_id,
               "input_revision": old_review["revision_id"], "run_id": old_run,
               "draft_version": 1, "review_version": 1}
    with pytest.raises(ReviewError) as error:
        await decide(principal, old_review["id"], command, str(uuid4()))
    assert error.value.status_code == 409


async def test_repeated_and_concurrent_reanalysis_keeps_one_pending_review(tenant):
    request_id = await new_request(tenant)
    await run_worker(tenant, (await get_request_meta(tenant, request_id))["active_run_id"])
    for _ in range(2):
        run_id = (await start_again(tenant, request_id))["run_id"]
        await run_worker(tenant, run_id)
        reviews = (await snapshot(tenant, request_id))["reviews"]
        assert len([v for v in reviews if v["status"] == "pending"]) == 1
    results = await asyncio.gather(start_again(tenant, request_id),
                                   start_again(tenant, request_id))
    active_run = (await get_request_meta(tenant, request_id))["active_run_id"]
    assert active_run in {r["run_id"] for r in results}
    await run_worker(tenant, active_run)
    reviews = (await snapshot(tenant, request_id))["reviews"]
    assert len([v for v in reviews if v["status"] == "pending"]) == 1
    assert next(v for v in reviews if v["status"] == "pending")["run_id"] == active_run
