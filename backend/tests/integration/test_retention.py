from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from starlette.requests import Request

from jevtriage.auth.core import Principal
from jevtriage.db.driver import get_driver
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.events import router as event_router
from jevtriage.ops.retention import RetentionConfig, cleanup
from jevtriage.policy.service import bootstrap_policy

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def tenant():
    value = f"retention_{uuid4().hex}"
    await bootstrap_policy(value)
    yield value
    driver = await get_driver()
    async with driver.session() as session:
        await (await session.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=value)).consume()


async def test_cleanup_preserves_work_records_and_updates_event_cursor(tenant, tmp_path):
    event_id, recent_event_id = f"event_{uuid4().hex}", f"event_{uuid4().hex}"
    idem_id, recent_idem_id = f"idem_{uuid4().hex}", f"idem_{uuid4().hex}"
    request_id, audit_id, session_id = f"request_{uuid4().hex}", f"audit_{uuid4().hex}", f"session_{uuid4().hex}"

    async def seed(tx):
        await (await tx.run(
            "MERGE (c:EventCounter {tenant_id:$tenant}) SET c.seq=2 "
            "CREATE (:Event {id:$event,tenant_id:$tenant,seq:1,created_at:datetime()-duration('P100D')}) "
            "CREATE (:Event {id:$recent,tenant_id:$tenant,seq:2,created_at:datetime()}) "
            "CREATE (:Idempotency {id:$idem,tenant_id:$tenant,scope:'test',key:'old',created_at:datetime()-duration('P40D')}) "
            "CREATE (:Idempotency {id:$idem_recent,tenant_id:$tenant,scope:'test',key:'new',created_at:datetime()}) "
            "CREATE (:Session {id:$session,tenant_id:$tenant,expires_at:datetime()-duration('P8D')}) "
            "CREATE (:Request {id:$request,tenant_id:$tenant}) "
            "CREATE (:Audit {id:$audit,tenant_id:$tenant})",
                tenant=tenant, event=event_id, recent=recent_event_id, idem=idem_id,
                idem_recent=recent_idem_id, session=session_id, request=request_id, audit=audit_id,
        )).consume()
    await write_tx(tenant, seed)

    config = RetentionConfig(event_days=90, idempotency_days=30, session_grace_days=7,
                             login_attempt_window_seconds=86400, batch_size=10)
    preview = await cleanup(data_dir=tmp_path, tenant_id=tenant, config=config, dry_run=True)
    assert preview["deleted"]["events"] == 1
    assert preview["deleted"]["idempotency"] == 1
    assert preview["deleted"]["sessions"] == 1

    async def unchanged(tx):
        return await (await tx.run(
            "MATCH (e:Event {tenant_id:$tenant,id:$event}) WITH count(e) AS events "
            "MATCH (i:Idempotency {tenant_id:$tenant,id:$idem}) WITH events,count(i) AS idem "
            "MATCH (s:Session {tenant_id:$tenant,id:$session}) WITH events,idem,count(s) AS sessions "
            "MATCH (r:Request {tenant_id:$tenant,id:$request}) WITH events,idem,sessions,count(r) AS requests "
            "MATCH (a:Audit {tenant_id:$tenant,id:$audit}) RETURN events,idem,sessions,requests,count(a) AS audits",
            event=event_id, idem=idem_id, session=session_id, request=request_id, audit=audit_id,
        )).single(strict=True)
    assert dict(await read_tx(tenant, unchanged)) == {"events": 1, "idem": 1, "sessions": 1, "requests": 1, "audits": 1}

    result = await cleanup(data_dir=tmp_path, tenant_id=tenant, config=config)
    assert result["deleted"] == preview["deleted"]
    async def retained(tx):
        row = await (await tx.run(
            "OPTIONAL MATCH (e:Event {tenant_id:$tenant,id:$event}) WITH count(e) AS recent_event "
            "OPTIONAL MATCH (i:Idempotency {tenant_id:$tenant,id:$idem}) RETURN recent_event,count(i) AS recent_idem",
            event=recent_event_id, idem=recent_idem_id,
        )).single(strict=True)
        return dict(row)
    assert await read_tx(tenant, retained) == {"recent_event": 1, "recent_idem": 1}
    async def state(tx):
        return await (await tx.run(
            "MATCH (c:EventCounter {tenant_id:$tenant}) "
            "OPTIONAL MATCH (e:Event {tenant_id:$tenant}) "
            "RETURN c.retained_from_seq AS retained, collect(e.seq) AS seqs",
            tenant=tenant,
        )).single(strict=True)
    assert (await read_tx(tenant, state))["retained"] == 2


async def test_cleanup_uses_configured_retention_and_rotated_journal_and_metrics(tmp_path):
    data_dir = tmp_path / "data"
    journal = data_dir / "journal"
    journal.mkdir(parents=True)
    expired_archive = journal / "archive-expired.jsonl"
    fresh_archive = journal / "archive-fresh.jsonl"
    expired_archive.write_text("old\n", encoding="utf-8")
    fresh_archive.write_text("new\n", encoding="utf-8")
    old = (datetime.now(UTC) - timedelta(days=100)).timestamp()
    import os
    os.utime(expired_archive, (old, old))

    from jevtriage.journal.collector import connect
    with connect(data_dir) as db:
        db.execute("INSERT INTO offsets(file_key,path,byte_offset,updated_at) VALUES('archive',?,?,?)",
                   (str(expired_archive), expired_archive.stat().st_size, datetime.now(UTC).isoformat()))
        db.execute("INSERT INTO events(event_id,attempt_id,kind,ts,payload) VALUES('old','a','x',?, '{}')", ((datetime.now(UTC)-timedelta(days=100)).isoformat(),))
        db.execute("INSERT INTO events(event_id,attempt_id,kind,ts,payload) VALUES('new','b','x',?, '{}')", (datetime.now(UTC).isoformat(),))
        db.commit()

    config = RetentionConfig(event_days=45, idempotency_days=15, session_grace_days=3,
                             login_attempt_window_seconds=86400, journal_days=45, metrics_days=45, batch_size=10)
    tenant = f"retention_files_{uuid4().hex}"
    result = await cleanup(data_dir=data_dir, tenant_id=tenant, config=config, dry_run=True)
    assert result["deleted"]["journal_files"] == 1
    assert result["deleted"]["metrics_events"] == 1
    assert expired_archive.exists()
    result = await cleanup(data_dir=data_dir, tenant_id=tenant, config=config)
    assert result["deleted"]["journal_files"] == 1
    assert not expired_archive.exists() and fresh_archive.exists()


async def test_sse_requires_snapshot_for_cursor_before_retained_from_seq(monkeypatch):
    tenant = f"retention_cursor_{uuid4().hex}"
    user = f"user_{tenant}"
    await apply_schema()
    async def seed(tx):
        await (await tx.run(
            "CREATE (:EventCounter {tenant_id:$tenant,seq:2,retained_from_seq:2}) "
            "CREATE (:Event {id:'retained-event-'+$tenant,tenant_id:$tenant,seq:2,kind:'policy.published', "
            "payload_json:'{}',audience:'tenant',created_at:datetime()})", tenant=tenant,
        )).consume()
    await write_tx(tenant, seed)
    request = Request({"type": "http", "method": "GET", "path": "/api/events/stream",
                       "headers": [(b"last-event-id", b"1")], "query_string": b"", "server": ("test", 80),
                       "client": ("test", 1234), "scheme": "http"})
    async def detect_cursor_handling(*_args):
        raise RuntimeError("router proceeded to subscription without requesting snapshot")
    monkeypatch.setattr(event_router, "_subscribe", detect_cursor_handling)
    try:
        response = await event_router.stream_events(
            request, after=None, max_events=None,
            principal=Principal(tenant, user, (), frozenset({"operator"})),
        )
        first = await anext(response.body_iterator)
        text = first.decode() if isinstance(first, bytes) else first
        assert "event: snapshot-required" in text and "retention_window" in text
    finally:
        driver = await get_driver()
        async with driver.session() as session:
            await (await session.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=tenant)).consume()
