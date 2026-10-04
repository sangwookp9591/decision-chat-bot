"""Cancellation fences a queued or leased judgment run."""
import asyncio
from uuid import uuid4

import pytest
import pytest_asyncio

from jevtriage.auth.core import Principal
from jevtriage.db.events import list_events
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.ingest.store import create_request, get_request_meta
from jevtriage.jobs.worker import Worker

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def tenant():
    value = f"cancel_{uuid4().hex}"
    await apply_schema()
    yield value
    async def cleanup(tx):
        await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=value)).consume()
    await write_tx(value, cleanup)


async def setup_run(tenant):
    from datetime import UTC, datetime
    result = await create_request(tenant, "author", "Test cancellation", [],
                                  f"key-{uuid4().hex}", f"hash-{uuid4().hex}",
                                  datetime.now(UTC).isoformat())
    run_id = (await get_request_meta(tenant, result["request_id"]))["active_run_id"]
    async def query(tx):
        row = await (await tx.run(
            "MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id",
            tenant=tenant, run=run_id,
        )).single(strict=True)
        return row["id"]
    return result["request_id"], run_id, await read_tx(tenant, query)


async def states(tenant, request_id, run_id, job_id):
    async def query(tx):
        row = await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
            "MATCH (r:Run {tenant_id:$tenant,id:$run}) "
            "MATCH (j:Job {tenant_id:$tenant,id:$job}) "
            "RETURN q.status AS request,r.status AS run,j.status AS job,r.cancelled_by AS actor",
            tenant=tenant, request=request_id, run=run_id, job=job_id,
        )).single(strict=True)
        return dict(row)
    return await read_tx(tenant, query)


async def test_pending_cancel_is_immediate_idempotent_and_audited(tenant, monkeypatch):
    import jevtriage.jobs.cancel as cancel_module
    cancel_run = cancel_module.cancel_run
    journal = []
    monkeypatch.setattr(cancel_module, "JournalWriter", lambda: type(
        "RecordingJournal", (), {"append": lambda self, record: journal.append(record)})())
    request_id, run_id, job_id = await setup_run(tenant)
    actor = Principal(tenant, "author", (), frozenset({"requester"}), True)
    first = await cancel_run(actor, request_id, run_id)
    second = await cancel_run(actor, request_id, run_id)
    assert first == second == {"request_id": request_id, "run_id": run_id, "status": "cancelled"}
    assert await states(tenant, request_id, run_id, job_id) == {
        "request": "cancelled", "run": "cancelled", "job": "cancelled", "actor": "author"}
    async def audit(tx):
        row = await (await tx.run(
            "MATCH (r:Run {tenant_id:$tenant,id:$run}) "
            "RETURN r.cancelled_at AS at,r.cancelled_step AS stage",
            tenant=tenant, run=run_id,
        )).single(strict=True)
        return dict(row)
    assert (await read_tx(tenant, audit))["at"] is not None
    assert (await read_tx(tenant, audit))["stage"] == "대기 중"
    assert not await Worker(tenants=[tenant]).claim_next()
    events = await list_events(tenant)
    assert sum(item["kind"] == "judgment.cancelled" and item["request_id"] == request_id
               for item in events) == 1
    assert [(item["kind"], item["status_code"]) for item in journal] == [
        ("worker_run", "cancelled")]


async def test_running_cancel_fences_late_result(tenant):
    from jevtriage.jobs.cancel import cancel_run
    request_id, run_id, job_id = await setup_run(tenant)
    entered, release = asyncio.Event(), asyncio.Event()
    async def handler(ctx):
        async with ctx.step("Jev 판단", kind="ai"):
            entered.set()
            await release.wait()
            await ctx.commit(lambda tx: tx.run(
                "MATCH (r:Run {tenant_id:$tenant,id:$run}) SET r.late_result=true",
                tenant=tenant, run=run_id), affects_request=True)
    worker = Worker(handlers={"judgment": handler}, lease_seconds=2, tenants=[tenant])
    work = asyncio.create_task(worker.process_job(tenant, job_id))
    await asyncio.wait_for(entered.wait(), 5)
    actor = Principal(tenant, "author", (), frozenset({"requester"}), True)
    await cancel_run(actor, request_id, run_id)
    async def stage(tx):
        row = await (await tx.run(
            "MATCH (r:Run {tenant_id:$tenant,id:$run}) RETURN r.cancelled_step AS stage",
            tenant=tenant, run=run_id,
        )).single(strict=True)
        return row["stage"]
    assert await read_tx(tenant, stage) == "Jev 판단"
    async def step_state(tx):
        row = await (await tx.run(
            "MATCH (s:RunStep {tenant_id:$tenant,run_id:$run,name:'Jev 판단'}) "
            "RETURN s.status AS status",
            tenant=tenant, run=run_id,
        )).single(strict=True)
        return row["status"]
    assert await read_tx(tenant, step_state) == "cancelled"
    release.set()
    await work
    assert (await states(tenant, request_id, run_id, job_id))["run"] == "cancelled"
    async def late(tx):
        row = await (await tx.run(
            "MATCH (r:Run {tenant_id:$tenant,id:$run}) RETURN r.late_result AS value",
            tenant=tenant, run=run_id)).single()
        return row["value"]
    assert await read_tx(tenant, late) is None


async def test_cancel_authorization_and_tenant_isolation(tenant):
    from jevtriage.jobs.cancel import cancel_run
    request_id, run_id, job_id = await setup_run(tenant)
    peer = Principal(tenant, "peer", (), frozenset({"requester"}), True)
    with pytest.raises(PermissionError):
        await cancel_run(peer, request_id, run_id)
    foreign = Principal("another_tenant", "author", (), frozenset({"operator"}), True)
    with pytest.raises(LookupError):
        await cancel_run(foreign, request_id, run_id)
    operator = Principal(tenant, "operator", (), frozenset({"operator"}), True)
    assert (await cancel_run(operator, request_id, run_id))["status"] == "cancelled"
    assert (await states(tenant, request_id, run_id, job_id))["actor"] == "operator"


async def test_completed_cancel_is_idempotent_and_completion_race_converges(tenant):
    from jevtriage.jobs.cancel import cancel_run
    author = Principal(tenant, "author", (), frozenset({"requester"}), True)
    request_id, run_id, job_id = await setup_run(tenant)
    worker = Worker(handlers={"judgment": lambda ctx: asyncio.sleep(0)}, tenants=[tenant])
    await worker.process_job(tenant, job_id)
    assert (await cancel_run(author, request_id, run_id))["status"] == "judgment_saved"
    assert (await cancel_run(author, request_id, run_id))["status"] == "judgment_saved"
    assert (await states(tenant, request_id, run_id, job_id))["job"] == "completed"

    # The result can commit immediately before the worker's final bookkeeping.
    request_id, run_id, job_id = await setup_run(tenant)
    async def committed(tx):
        await (await tx.run(
            "MATCH (r:Run {tenant_id:$tenant,id:$run}) "
            "SET r.status='running',r.first_judgment_committed_at=datetime()",
            tenant=tenant, run=run_id,
        )).consume()
    await write_tx(tenant, committed)
    assert (await cancel_run(author, request_id, run_id))["status"] == "judgment_saved"
    assert (await states(tenant, request_id, run_id, job_id))["job"] == "completed"

    request_id, run_id, job_id = await setup_run(tenant)
    entered, release = asyncio.Event(), asyncio.Event()
    async def handler(ctx):
        entered.set()
        await release.wait()
    racing_worker = Worker(handlers={"judgment": handler}, tenants=[tenant])
    work = asyncio.create_task(racing_worker.process_job(tenant, job_id))
    await asyncio.wait_for(entered.wait(), 5)
    release.set()
    await asyncio.gather(work, cancel_run(author, request_id, run_id))
    value = await states(tenant, request_id, run_id, job_id)
    assert (value["run"], value["job"]) in {
        ("cancelled", "cancelled"), ("judgment_saved", "completed")}
