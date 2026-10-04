import asyncio
from uuid import uuid4

import pytest
import pytest_asyncio

from jevtriage.db.events import append_event_in_tx, list_events
from jevtriage.db.jobs import OwnershipLost, create_job, heartbeat
from jevtriage.db.requests import StaleRun, add_input_revision, create_request, set_active_run
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.jobs.worker import Worker
from jevtriage.observe.trace_store import get_trace

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def tenant():
    value = f"t08_{uuid4().hex}"
    await apply_schema()
    yield value
    async def cleanup(tx):
        await (await tx.run("MATCH (n {tenant_id: $tenant_id}) DETACH DELETE n",
                            tenant_id=value)).consume()
    await write_tx(value, cleanup)


async def make_job(tenant, *, kind="test.sleep", age_seconds=0):
    request_id = await create_request(tenant, "tester")
    revision_id, _ = await add_input_revision(tenant, request_id, "tester")
    run_id = f"run_{uuid4().hex}"
    async def create(tx):
        await (await tx.run(
            "CREATE (:Run {id: $run_id, tenant_id: $tenant_id, "
            "request_id: $request_id, input_revision_id: $revision_id, "
            "kind: 'normal', status: 'pending', job_kind: $kind, "
            "created_at: datetime() - duration({seconds: $age}), "
            "config_version: 3, model_version: 'model-x', qset_version: 'q1', "
            "schema_version: 's1', catalog_version: 'c1', policy_version: 'p1'})",
            tenant_id=tenant, run_id=run_id, request_id=request_id,
            revision_id=revision_id, kind=kind, age=age_seconds,
        )).consume()
    await write_tx(tenant, create)
    await set_active_run(tenant, request_id, run_id, revision_id)
    job_id = await create_job(tenant, run_id, revision_id)
    return request_id, revision_id, run_id, job_id


async def get_job(tenant, job_id):
    async def op(tx):
        result = await tx.run("MATCH (j:Job {tenant_id: $tenant_id, id: $job_id}) RETURN j",
                              tenant_id=tenant, job_id=job_id)
        return dict((await result.single(strict=True))["j"])
    return await read_tx(tenant, op)


async def test_candidate_discovery_respects_worker_tenant_allowlist(tenant):
    other = f"t08_{uuid4().hex}"
    await apply_schema()
    await create_job(tenant, "run_primary", "rev_primary")
    await create_job(other, "run_other", "rev_other")
    try:
        rows = await Worker(tenants=[tenant]).candidates()
        assert rows
        assert {row["tenant_id"] for row in rows} == {tenant}
    finally:
        async def cleanup(tx):
            await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=other)).consume()
        await write_tx(other, cleanup)


async def test_takeover_rejects_old_steps_results_events_and_heartbeat(tenant, tmp_path):
    _, _, run_id, job_id = await make_job(tenant)
    entered = asyncio.Event()
    release = asyncio.Event()
    old_errors = []

    async def old_handler(ctx):
        async with ctx.step("old", kind="ai"):
            entered.set()
            await release.wait()
            try:
                await ctx.commit(lambda tx: append_event_in_tx(
                    tx, tenant, "old_result", {"run_id": run_id}), affects_request=True)
            except OwnershipLost as exc:
                old_errors.append(type(exc).__name__)
                raise

    async def new_handler(ctx):
        async with ctx.step("new", kind="code"):
            await ctx.commit(lambda tx: append_event_in_tx(
                tx, tenant, "new_result", {"run_id": run_id}), affects_request=True)

    a = Worker(lease_seconds=0.3, poll_seconds=0.05, handlers={"test.sleep": old_handler})
    b = Worker(lease_seconds=2, handlers={"test.sleep": new_handler})
    async def no_heartbeat(ctx, task):
        await asyncio.Event().wait()
    a._heartbeat = no_heartbeat
    task_a = asyncio.create_task(a.process_job(tenant, job_id))
    await asyncio.wait_for(entered.wait(), 3)
    owner_a = await get_job(tenant, job_id)
    await asyncio.sleep(0.4)
    await b.process_job(tenant, job_id)
    with pytest.raises(OwnershipLost):
        await heartbeat(tenant, job_id, a.owner_id, owner_a["lease_generation"], 1)
    release.set()
    await task_a
    assert old_errors == ["OwnershipLost"]
    events = await list_events(tenant)
    assert [(event["kind"], event["payload"].get("status"),
             event["payload"].get("step_name")) for event in events] == [
        ("run.step", "running", "old"),
        ("run.step", "running", "new"),
        ("new_result", None, None),
        ("run.step", "succeeded", "new"),
    ]
    trace = await get_trace(tenant, run_id)
    assert trace["run"]["status"] == "judgment_saved"
    assert len(trace["run"]["attempts"]) == 2
    assert trace["run"]["attempts"][0]["status"] == "interrupted"
    assert trace["run"]["attempts"][1]["status"] == "judgment_saved"
    assert [step["name"] for step in trace["steps"]] == ["old", "new"]
    assert trace["steps"][0]["status"] == "failed"
    assert trace["steps"][0]["error_class"] == "LeaseExpired"
    assert trace["steps"][1]["status"] == "succeeded"
    assert trace["steps"][1]["versions"]["config"] == 3
    assert trace["steps"][1]["duration_ms"] >= 0


async def test_old_run_cannot_change_request_pointer(tenant):
    request_id, revision_id, old_run, job_id = await make_job(tenant)
    new_run = f"run_{uuid4().hex}"
    async def create(tx):
        await (await tx.run(
            "CREATE (:Run {id: $id, tenant_id: $tenant_id, request_id: $request_id, "
            "input_revision_id: $revision_id, kind: 'normal'})",
            id=new_run, tenant_id=tenant, request_id=request_id,
            revision_id=revision_id,
        )).consume()
    await write_tx(tenant, create)

    async def handler(ctx):
        await set_active_run(tenant, request_id, new_run, revision_id,
                             expected_active_run_id=old_run)
        with pytest.raises(StaleRun):
            await ctx.commit(lambda tx: append_event_in_tx(
                tx, tenant, "stale_result", {}), affects_request=True)

    worker = Worker(handlers={"test.sleep": handler})
    await worker.process_job(tenant, job_id)
    assert not any(e["kind"] == "stale_result" for e in await list_events(tenant))


async def test_restart_recovery_and_deadline_journal(tenant, tmp_path):
    _, _, run_id, job_id = await make_job(tenant)
    entered = asyncio.Event()

    async def interrupted(ctx):
        entered.set()
        await asyncio.Event().wait()

    a = Worker(lease_seconds=0.2, handlers={"test.sleep": interrupted})
    task = asyncio.create_task(a.process_job(tenant, job_id))
    await asyncio.wait_for(entered.wait(), 3)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.sleep(0.3)

    async def recovered(ctx):
        async with ctx.step("recovered", kind="rule"):
            pass

    b = Worker(lease_seconds=1, handlers={"test.sleep": recovered})
    await b.process_job(tenant, job_id)
    trace = await get_trace(tenant, run_id)
    assert [a["status"] for a in trace["run"]["attempts"]] == ["interrupted", "judgment_saved"]
    assert trace["steps"][0]["status"] == "succeeded"

    _, _, expired_run, expired_job = await make_job(tenant, age_seconds=2)
    from jevtriage.journal.writer import JournalWriter
    c = Worker(deadline_seconds=1, handlers={"test.sleep": recovered},
               journal=JournalWriter(tmp_path))
    await c.process_job(tenant, expired_job)
    expired = await get_trace(tenant, expired_run)
    assert expired["run"]["status"] == "failed"
    assert expired["run"]["error_class"] == "DeadlineExceeded"
    c.journal.flush()
    assert '"kind":"worker_run"' in (tmp_path / "journal" / "current.jsonl").read_text()


async def test_poll_loop_records_non_successful_branch(tenant):
    _, _, run_id, job_id = await make_job(tenant, kind="test.branch")

    async def handler(ctx):
        async with ctx.step("manual_review", kind="human", completion_status="waiting_human"):
            pass

    worker = Worker(handlers={"test.branch": handler}, poll_seconds=0.02)
    loop = asyncio.create_task(worker.run())
    try:
        for _ in range(100):
            if (await get_job(tenant, job_id))["status"] == "completed":
                break
            await asyncio.sleep(0.02)
        else:
            pytest.fail("worker did not poll and complete Job")
    finally:
        worker.stop()
        await loop
    trace = await get_trace(tenant, run_id)
    assert trace["steps"][0]["status"] == "waiting_human"
    assert trace["run"]["status"] == "judgment_saved"
