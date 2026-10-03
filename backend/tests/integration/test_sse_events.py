import asyncio
import json
from unittest.mock import patch
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from jevtriage.auth.core import Principal
from jevtriage.db.driver import get_driver
from jevtriage.db.events import append_event
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import write_tx
from jevtriage.events import router as event_router
from jevtriage.main import create_app


@pytest_asyncio.fixture(loop_scope="session")
async def stream_graph():
    tenant = f"sse_{uuid4().hex}"
    user = f"usr_{tenant}"
    request_id = f"req_{uuid4().hex}"
    hidden_id = f"req_{uuid4().hex}"
    async def seed(tx):
        await (await tx.run(
            "CREATE (:Request {id:$request_id, tenant_id:$tenant, created_by:$user, "
            "org_ids:[], shared_org_ids:[], status:'processing', active_run_id:'run_active'}), "
            "(:Request {id:$hidden_id, tenant_id:$tenant, created_by:'other_user', "
            "org_ids:[], shared_org_ids:[], status:'processing'})",
            tenant=tenant, user=user, request_id=request_id, hidden_id=hidden_id,
        )).consume()
    await apply_schema()
    await write_tx(tenant, seed)
    yield tenant, user, request_id, hidden_id
    async def cleanup():
        driver = await get_driver()
        async with driver.session() as session:
            await (await session.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=tenant)).consume()
    await cleanup()


def _client(graph):
    tenant, user, *_ = graph
    app = create_app()
    @app.middleware("http")
    async def principal_override(request, call_next):
        current_user = request.headers.get("X-Test-User", user)
        request.state.principal = Principal(tenant, current_user, (), frozenset({"requester"}))
        return await call_next(request)
    return TestClient(app)


def _parse_sse(response_text):
    events = []
    for block in response_text.strip().split("\n\n"):
        item = {}
        for line in block.splitlines():
            if line.startswith("id: "): item["id"] = int(line[4:])
            if line.startswith("event: "): item["event"] = line[7:]
            if line.startswith("data: "): item["data"] = json.loads(line[6:])
        if item:
            events.append(item)
    return events


def _read_events(client, **kwargs):
    chunks = ""
    with client.stream("GET", "/api/events/stream", **kwargs) as response:
        assert response.status_code == 200
        for chunk in response.iter_text():
            chunks += chunk
            events = _parse_sse(chunks)
            if len(events) >= 2:
                return response.status_code, events
    return response.status_code, _parse_sse(chunks)


@pytest.mark.asyncio(loop_scope="session")
async def test_stream_order_resume_scope_and_snapshot(stream_graph):
    tenant, _, visible, hidden = stream_graph
    async def seed_events():
        first = await append_event(tenant, "progress", {"status": "queued", "source_text": "secret"}, request_id=visible)
        await append_event(tenant, "progress", {"status": "hidden"}, request_id=hidden)
        third = await append_event(tenant, "completed", {"status": "done"}, request_id=visible)
        policy = await append_event(tenant, "policy.published", {"status": "published", "version": 4, "secret": "hidden"})
        rule = await append_event(tenant, "rule.decision", {"status": "approved", "rule_id": "rule_x", "private_note": "hidden"})
        return first, third, policy, rule
    first, third, _policy, _rule = await asyncio.wait_for(seed_events(), 10)
    client = _client(stream_graph)
    with client:
        _, parsed = await asyncio.to_thread(_read_events, client, headers={"Last-Event-ID": "0"}, params={"max_events": 2})
        assert [item["id"] for item in parsed] == [first["seq"], third["seq"]]
        assert [item["event"] for item in parsed] == ["progress", "completed"]
        assert all(item["data"]["request_id"] == visible for item in parsed)
        assert "source_text" not in json.dumps(parsed)
        _, tenant_events = await asyncio.to_thread(_read_events, client, headers={"Last-Event-ID": str(third["seq"])}, params={"max_events": 2})
        assert [event["event"] for event in tenant_events] == ["policy.published", "rule.decision"]
        assert tenant_events[0]["data"] == {"request_id": None, "run_id": None, "status": "published", "version": 4}
        assert tenant_events[1]["data"] == {"request_id": None, "run_id": None, "status": "approved", "rule_id": "rule_x"}
        _, resumed = await asyncio.to_thread(_read_events, client, headers={"Last-Event-ID": str(first["seq"])}, params={"max_events": 1})
        assert [item["id"] for item in resumed] == [third["seq"]]
        snapshot = await asyncio.to_thread(client.get, "/api/events/snapshot", params={"request_id": visible})
        assert snapshot.json() == {"request_id": visible, "status": "processing", "active_run_id": "run_active", "latest_seq": third["seq"]}
        hidden_response = await asyncio.to_thread(client.get, "/api/events/snapshot", params={"request_id": hidden})
        assert hidden_response.status_code == 404
        with client.stream("GET", "/api/events/stream", headers={"Last-Event-ID": str(third["seq"] + 10)}) as response:
            assert "event: snapshot-required" in "".join(response.iter_text())
        async def age_cursor(tx):
            await (await tx.run(
                "MATCH (e:Event {tenant_id:$tenant_id, seq:$seq}) "
                "SET e.created_at = datetime() - duration('P8D')",
                tenant_id=tenant, seq=first["seq"],
            )).consume()
        await write_tx(tenant, age_cursor)
        with client.stream("GET", "/api/events/stream", headers={"Last-Event-ID": str(first["seq"])}) as response:
            assert "event: snapshot-required" in "".join(response.iter_text())


def test_stream_requires_authentication():
    with TestClient(create_app()) as client:
        assert client.get("/api/events/stream").status_code == 401
        assert client.get("/api/events/snapshot", params={"request_id": "req_missing"}).status_code == 401


@pytest.mark.asyncio(loop_scope="session")
async def test_multiple_connections_share_order_without_leaking_requests(stream_graph):
    tenant, _user, visible, hidden = stream_graph
    first = await append_event(tenant, "progress", {"status": "one"}, request_id=visible)
    private = await append_event(tenant, "progress", {"status": "private"}, request_id=hidden)
    last = await append_event(tenant, "completed", {"status": "two"}, request_id=visible)
    client = _client(stream_graph)
    scans = metadata_queries = 0
    original_scan = event_router.list_events
    original_metas = event_router._request_metas

    async def counted_scan(*args, **kwargs):
        nonlocal scans
        scans += 1
        return await original_scan(*args, **kwargs)

    async def counted_metas(*args, **kwargs):
        nonlocal metadata_queries
        metadata_queries += 1
        return await original_metas(*args, **kwargs)

    with client, patch.object(event_router, "list_events", counted_scan), patch.object(event_router, "_request_metas", counted_metas):
        async def read(headers, count):
            return await asyncio.to_thread(
                _read_events, client, headers=headers,
                params={"after": first["seq"] - 1, "max_events": count},
            )
        # Both users share a tenant poller while authorization remains per connection.
        calls = [read({}, 2) for _ in range(6)]
        calls += [read({"X-Test-User": "other_user"}, 1) for _ in range(4)]
        results = await asyncio.wait_for(asyncio.gather(*calls), 20)
    assert scans < 10
    assert metadata_queries < 10
    for _, events in results[:6]:
        assert [event["id"] for event in events] == [first["seq"], last["seq"]]
        assert len({event["id"] for event in events}) == 2
    for _, events in results[6:]:
        assert [event["id"] for event in events] == [private["seq"]]
        assert all(event["data"]["request_id"] == hidden for event in events)


@pytest.mark.asyncio(loop_scope="session")
async def test_new_events_fan_out_to_waiting_connections(stream_graph):
    tenant, _, visible, _hidden = stream_graph
    async def read(client):
        return await asyncio.to_thread(_read_events, client, params={"max_events": 2})

    client = _client(stream_graph)
    with client:
        readers = [asyncio.create_task(read(client)) for _ in range(5)]
        await asyncio.sleep(0.3)
        first = await append_event(tenant, "progress", {"status": "running"}, request_id=visible)
        last = await append_event(tenant, "completed", {"status": "done"}, request_id=visible)
        results = await asyncio.wait_for(asyncio.gather(*readers), 10)
    assert all([event["id"] for event in events] == [first["seq"], last["seq"]]
               for _, events in results)
