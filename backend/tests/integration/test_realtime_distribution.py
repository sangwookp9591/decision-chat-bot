import asyncio
import os
import shutil
import socket
import sys
import time
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from redis.exceptions import RedisError

from jevtriage.auth.core import Principal
from jevtriage.db.events import append_event, list_events
from jevtriage.db.tx import write_tx
from jevtriage.main import create_app
from jevtriage.realtime.notifier import ConnectionSlots, publish_job
from jevtriage.realtime.subscriber import JobSubscriber, TenantSubscriber

_API_SCRIPT = """
import os
import sys
import uvicorn
from fastapi import Request
from jevtriage.auth.core import Principal
from jevtriage.db.events import append_event
from jevtriage.main import create_app

app = create_app()

@app.middleware('http')
async def test_principal(request: Request, call_next):
    request.state.principal = Principal(os.environ['TEST_TENANT'], 'user_test', (), frozenset({'requester'}))
    return await call_next(request)

@app.post('/emit')
async def emit():
    return await append_event(os.environ['TEST_TENANT'], 'policy.published', {'version': 1})

uvicorn.run(app, host='127.0.0.1', port=int(sys.argv[1]), log_level='error')
"""


def _free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def test_progress_payload_rejects_unrecognized_nested_values():
    from jevtriage.events.router import _safe_progress_fields

    assert _safe_progress_fields({
        "classifications": {"ai_need": "raw source text"},
        "confidences": {"ai_need": "0.8"},
        "risk_flags": {"clinical_safety": "yes"},
        "preliminary": "true", "task_count": -1,
    }) == {}


@pytest.mark.asyncio
async def test_progress_event_safe_fields_obey_request_scope():
    tenant = f"realtime_{uuid4().hex}"
    visible = f"req_{uuid4().hex}"
    hidden = f"req_{uuid4().hex}"

    async def seed(tx):
        await (await tx.run(
            "CREATE (:Request {id:$visible,tenant_id:$tenant,created_by:'user_test',org_ids:[],shared_org_ids:[]}),"
            "(:Request {id:$hidden,tenant_id:$tenant,created_by:'other_user',org_ids:[],shared_org_ids:[]})",
            visible=visible, hidden=hidden, tenant=tenant,
        )).consume()

    await write_tx(tenant, seed)
    await append_event(tenant, "judgment.partial", {"classifications": {"ai_need": "불필요"}}, request_id=hidden)
    event = await append_event(tenant, "judgment.partial", {
        "classifications": {"ai_need": "필요"}, "confidences": {"ai_need": 0.8},
        "risk_flags": {"clinical_safety": True}, "preliminary": True, "source_text": "never-expose",
    }, request_id=visible)
    app = create_app()

    @app.middleware("http")
    async def principal(request, call_next):
        request.state.principal = Principal(tenant, "user_test", (), frozenset({"requester"}))
        return await call_next(request)

    def read():
        with TestClient(app) as client:
            return client.get("/api/events/stream", params={"max_events": 1}).text

    body = await asyncio.to_thread(read)
    assert f"id: {event['seq']}" in body
    assert '"classifications":{"ai_need":"필요"}' in body
    assert '"confidences":{"ai_need":0.8}' in body
    assert '"risk_flags":{"clinical_safety":true}' in body
    assert '"preliminary":true' in body
    assert "never-expose" not in body
    assert "불필요" not in body


@pytest.mark.asyncio
async def test_two_api_processes_deliver_committed_event(redis_url, tmp_path):
    tenant = f"realtime_{uuid4().hex}"
    ports = [_free_port(), _free_port()]
    processes = []
    for index, port in enumerate(ports):
        env = {**os.environ, "REDIS_URL": redis_url, "TEST_TENANT": tenant,
               "DATA_DIR": str(tmp_path / str(index))}
        processes.append(await asyncio.create_subprocess_exec(
            sys.executable, "-c", _API_SCRIPT, str(port), env=env,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        ))
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            for port in ports:
                for _ in range(100):
                    try:
                        if (await client.get(f"http://127.0.0.1:{port}/api/health")).status_code == 200:
                            break
                    except httpx.ConnectError:
                        await asyncio.sleep(0.05)
                else:
                    pytest.fail(f"API instance on {port} did not start")
            async with client.stream("GET", f"http://127.0.0.1:{ports[1]}/api/events/stream?max_events=1") as stream:
                assert stream.status_code == 200
                started = time.monotonic()
                emitted = (await client.post(f"http://127.0.0.1:{ports[0]}/emit")).json()
                lines = []
                async for line in stream.aiter_lines():
                    lines.append(line)
                assert f"id: {emitted['seq']}" in lines
                assert time.monotonic() - started < 2
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            try:
                await asyncio.wait_for(process.wait(), 5)
            except TimeoutError:
                process.kill()
                await process.wait()


@pytest.mark.asyncio
async def test_committed_event_wakes_another_subscriber(redis_url):
    tenant = f"realtime_{uuid4().hex}"
    subscriber = TenantSubscriber(tenant, redis_url)
    await subscriber.start()
    try:
        for _ in range(100):
            if subscriber.connected:
                break
            await asyncio.sleep(0.01)
        assert subscriber.connected
        await subscriber.wait(1)
        first = await append_event(tenant, "progress", {"status": "one"})
        await asyncio.wait_for(subscriber.wait(), 2)
        assert [event["seq"] for event in await list_events(tenant)] == [first["seq"]]

        async def abort(tx):
            from jevtriage.db.events import append_event_in_tx
            await append_event_in_tx(tx, tenant, "progress", {"status": "rolled_back"})
            raise RuntimeError("rollback")

        with pytest.raises(RuntimeError):
            await write_tx(tenant, abort)
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(subscriber.wait(), 0.2)
        assert [event["seq"] for event in await list_events(tenant)] == [first["seq"]]
    finally:
        await subscriber.close()


@pytest.mark.asyncio
async def test_publish_failure_does_not_undo_committed_event(monkeypatch):
    from jevtriage.db import tx as db_tx
    from jevtriage.realtime import notifier

    tenant = f"realtime_{uuid4().hex}"

    async def failed_publish(*_args):
        raise OSError("Redis unavailable")

    monkeypatch.setattr(notifier, "publish_event", failed_publish)
    before = db_tx.after_commit_failures
    event = await append_event(tenant, "policy.published", {"version": 1})
    assert [item["seq"] for item in await list_events(tenant)] == [event["seq"]]
    assert db_tx.after_commit_failures == before + 1


@pytest.mark.asyncio
async def test_job_channel_and_global_connection_limit(redis_url):
    from redis.asyncio import Redis

    client = Redis.from_url(redis_url)
    pubsub = client.pubsub()
    await pubsub.subscribe("jobs")
    await pubsub.get_message(timeout=1)
    job_listener = JobSubscriber(redis_url)
    await job_listener.start()
    try:
        for _ in range(100):
            if job_listener.connected:
                break
            await asyncio.sleep(0.01)
        assert job_listener.connected
        await job_listener.wait(1)
        assert await publish_job("job_test", redis_url)
        await asyncio.wait_for(job_listener.wait(), 2)
        message = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True, timeout=2), 3)
        assert message["data"] == b"job_test"
        first = ConnectionSlots(redis_url, limit=1)
        second = ConnectionSlots(redis_url, limit=1)
        token = await first.acquire()
        assert token
        assert await second.acquire() is None
        await first.release(token)
        new_token = await second.acquire()
        assert new_token
        await second.release(new_token)
        expiring = ConnectionSlots(redis_url, limit=1, ttl=1)
        token = await expiring.acquire()
        assert token
        await asyncio.sleep(0.6)
        await expiring.refresh(token)
        await asyncio.sleep(0.6)
        assert await second.acquire() is None
        await expiring.release(token)
    finally:
        await job_listener.close()
        await pubsub.aclose()
        await client.aclose()


@pytest.mark.asyncio
async def test_tenant_hub_replays_missed_notification(redis_url, monkeypatch):
    from jevtriage.events.router import _TenantHub
    from jevtriage.realtime import notifier

    tenant = f"realtime_{uuid4().hex}"
    hub = _TenantHub(tenant, 0)
    queue = hub.subscribe(0)
    try:
        for _ in range(100):
            if hub.listener.connected:
                break
            await asyncio.sleep(0.01)
        assert hub.listener.connected

        async def dropped(*_args, **_kwargs):
            return False

        monkeypatch.setattr(notifier, "publish_event", dropped)
        event = await append_event(tenant, "policy.published", {"version": 1})
        batch, _metas, scanned = await asyncio.wait_for(queue.get(), 6)
        assert scanned == event["seq"]
        assert [item["seq"] for item in batch] == [event["seq"]]
    finally:
        if hub.task:
            hub.task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await hub.task


@pytest.mark.asyncio
async def test_unavailable_redis_uses_local_connection_slots():
    slots = ConnectionSlots("redis://localhost:6399/15", limit=1)
    token = await slots.acquire()
    assert token and token.startswith("local:")
    assert await slots.acquire() is None
    await slots.release(token)
    assert await slots.acquire()


@pytest.mark.asyncio
async def test_redis_outage_fallback_and_recovery(monkeypatch):
    binary = shutil.which("redis-server")
    if not binary:
        pytest.skip("redis-server executable is unavailable")
    from redis.asyncio import Redis

    from jevtriage.config import get_settings
    from jevtriage.events.router import _TenantHub

    port = _free_port()
    url = f"redis://127.0.0.1:{port}/15"
    monkeypatch.setenv("REDIS_URL", url)
    get_settings.cache_clear()
    tenant = f"realtime_{uuid4().hex}"
    server = None
    hub = _TenantHub(tenant, 0)
    queue = hub.subscribe(0)

    async def start_server():
        process = await asyncio.create_subprocess_exec(
            binary, "--port", str(port), "--save", "", "--appendonly", "no",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        client = Redis.from_url(url)
        for _ in range(100):
            try:
                if await client.ping():
                    break
            except (RedisError, OSError):
                await asyncio.sleep(0.02)
        else:
            pytest.fail("isolated Redis did not start")
        await client.aclose()
        return process

    try:
        server = await start_server()
        for _ in range(100):
            if hub.listener.connected:
                break
            await asyncio.sleep(0.02)
        assert hub.listener.connected
        server.terminate()
        await asyncio.wait_for(server.wait(), 5)
        server = None
        for _ in range(100):
            if not hub.listener.connected:
                break
            await asyncio.sleep(0.02)
        assert not hub.listener.connected
        first = await append_event(tenant, "policy.published", {"version": 1})
        batch, _, _ = await asyncio.wait_for(queue.get(), 3)
        assert [item["seq"] for item in batch] == [first["seq"]]
        hub.subscribers[queue] = first["seq"]

        server = await start_server()
        for _ in range(100):
            if hub.listener.connected:
                break
            await asyncio.sleep(0.02)
        assert hub.listener.connected
        second = await append_event(tenant, "policy.published", {"version": 2})
        batch, _, _ = await asyncio.wait_for(queue.get(), 3)
        assert batch[-1]["seq"] == second["seq"]
    finally:
        if hub.task:
            hub.task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await hub.task
        if server:
            server.terminate()
            await asyncio.wait_for(server.wait(), 5)
        get_settings.cache_clear()


@pytest.fixture
def redis_url(monkeypatch):
    from jevtriage.config import get_settings

    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/15")
    get_settings.cache_clear()
    yield "redis://localhost:6379/15"
    get_settings.cache_clear()
