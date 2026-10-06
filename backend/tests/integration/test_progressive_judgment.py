"""Progress is durable before independent downstream Decision AI calls finish."""
import asyncio
import json
import threading
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException

from ildongi.auth.core import Principal
from ildongi.db.events import list_events
from ildongi.db.schema import apply_schema
from ildongi.db.tx import read_tx, write_tx
from ildongi.ingest.service import submit
from ildongi.ingest.store import create_request, get_request_meta
from ildongi.jobs.worker import Worker
from ildongi.judgment.ai_client import AiClient
from ildongi.judgment.progress import get_progress, progress
from ildongi.judgment.service import execute_judgment
from ildongi.judgment.store import get_judgment

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def tenant():
    value = f"perf1_{uuid4().hex}"
    await apply_schema()
    yield value
    async def cleanup(tx):
        await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=value)).consume()
    await write_tx(value, cleanup)


async def test_partial_result_precedes_evidence_and_final_commit(tenant):
    created = await create_request(tenant, "tester", "새 업무 요청을 분류해 주세요.", [],
                                   uuid4().hex, uuid4().hex, datetime.now(UTC).isoformat())
    request_id = created["request_id"]
    run_id = (await get_request_meta(tenant, request_id))["active_run_id"]

    async def job(tx):
        return (await (await tx.run(
            "MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id",
            tenant=tenant, run=run_id)).single(strict=True))["id"]

    evidence_started = threading.Event()
    tasks_started = threading.Event()
    release = threading.Event()

    class SlowClient(AiClient):
        def ask(self, state, questions):
            if "is_evidence" in questions:
                evidence_started.set()
                release.wait(timeout=10)
            elif any(k.startswith("needed_") for k in questions):
                tasks_started.set()
                release.wait(timeout=10)
            return super().ask(state, questions)

    async def handler(ctx):
        await execute_judgment(ctx, SlowClient("", mode="mock"))

    worker = Worker(handlers={"judgment": handler})
    task = asyncio.create_task(worker.process_job(tenant, await read_tx(tenant, job)))
    try:
        await asyncio.wait_for(asyncio.to_thread(evidence_started.wait), timeout=5)
        await asyncio.wait_for(asyncio.to_thread(tasks_started.wait), timeout=5)
        progress = await get_progress(tenant, request_id)
        assert progress["run_id"] == run_id
        assert progress["status"] == "processing"
        assert progress["preliminary"]["classifications"]["ai_need"] == "정보 부족"
        assert progress["final"] is False
        assert progress["evidence_ready"] is False
        assert progress["tasks_ready"] is False
        assert await get_judgment(tenant, request_id, run_id) is None
        assert (await get_request_meta(tenant, request_id)).get("assignment_id") is None
        events = await list_events(tenant)
        partial = [event for event in events if event["kind"] == "judgment.partial"
                   and event["run_id"] == run_id]
        assert len(partial) == 1
        assert partial[0]["payload"]["preliminary"] is True
        assert "새 업무 요청" not in json.dumps(partial[0]["payload"], ensure_ascii=False)
    finally:
        release.set()
        await asyncio.wait_for(task, timeout=10)
    progress = await get_progress(tenant, request_id)
    assert progress["final"] is True
    assert progress["evidence_ready"] is True
    assert progress["tasks_ready"] is True
    async def staged(tx):
        return await (await tx.run(
            "MATCH (r:Run {tenant_id:$tenant,id:$run}) "
            "RETURN r.evidence_json AS evidence,r.tasks_json AS tasks",
            tenant=tenant, run=run_id)).single(strict=True)
    staged_results = await read_tx(tenant, staged)
    assert "ai_need" in json.loads(staged_results["evidence"])
    assert json.loads(staged_results["tasks"])
    assert "새 업무 요청" not in staged_results["evidence"]
    events = await list_events(tenant)
    kinds = [event["kind"] for event in events if event["run_id"] == run_id]
    assert "judgment.evidence_ready" in kinds
    assert "judgment.tasks_ready" in kinds
    saved = next(event for event in events if event["kind"] == "judgment_saved"
                 and event["run_id"] == run_id)
    assert saved["payload"]["classifications"]["ai_need"] == "정보 부족"


async def test_submit_emits_one_received_event_for_idempotent_request(tenant):
    key = uuid4().hex
    first = await submit(tenant, "tester", "접수 이벤트 확인", [], key)
    second = await submit(tenant, "tester", "접수 이벤트 확인", [], key)
    assert first == second
    events = [event for event in await list_events(tenant)
              if event["kind"] == "request.received"
              and event["request_id"] == first["request_id"]]
    assert len(events) == 1
    assert events[0]["payload"] == {
        "request_id": first["request_id"], "run_id": events[0]["run_id"],
        "status": "judgment_pending"}

    owner = Principal(tenant, "tester", (), frozenset({"requester"}), True)
    stranger = Principal(tenant, "stranger", (), frozenset({"requester"}), True)
    assert (await progress(first["request_id"], None, owner))["request_id"] == first["request_id"]
    with pytest.raises(HTTPException) as denied:
        await progress(first["request_id"], None, stranger)
    assert denied.value.status_code == 404


async def test_worker_wakes_from_idle_backoff_without_redis(monkeypatch):
    from ildongi.config import get_settings
    monkeypatch.setattr(get_settings(), "redis_url", None)
    worker = Worker(poll_seconds=1, max_poll_seconds=8)
    first = asyncio.Event()
    second = asyncio.Event()
    calls = 0

    async def claim():
        nonlocal calls
        calls += 1
        if calls == 1:
            first.set()
        elif calls == 2:
            second.set()

    worker.claim_next = claim
    running = asyncio.create_task(worker.run())
    try:
        await asyncio.wait_for(first.wait(), 2)
        Worker.notify_new_job()
        await asyncio.wait_for(second.wait(), 0.25)
    finally:
        worker.stop()
        await asyncio.wait_for(running, 2)
