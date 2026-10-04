"""Authenticated, tenant scoped event stream and recovery snapshots."""

import asyncio
import json
import os
import time
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from jevtriage.auth.core import Principal, can_view_request, get_principal, session_principal
from jevtriage.db.events import list_events
from jevtriage.db.tx import read_tx
from jevtriage.journal.writer import JournalWriter
from jevtriage.judgment.questions import OPTIONS
from jevtriage.realtime.notifier import ConnectionSlots
from jevtriage.realtime.subscriber import TenantSubscriber

router = APIRouter(prefix="/api/events", tags=["events"])
POLL_SECONDS = float(os.getenv("SSE_POLL_SECONDS", "0.2"))
MAX_CONNECTIONS = int(os.getenv("SSE_MAX_CONNECTIONS", "100"))
MAX_AFTER_AGE_SECONDS = int(os.getenv("SSE_MAX_AFTER_AGE_SECONDS", "604800"))
SESSION_RECHECK_SECONDS = float(os.getenv("SSE_SESSION_RECHECK_SECONDS", "15"))
_slots = ConnectionSlots(limit=MAX_CONNECTIONS)
_journal = JournalWriter()
_hubs: dict[str, "_TenantHub"] = {}
_hubs_lock = asyncio.Lock()


class _SlotStreamingResponse(StreamingResponse):
    def __init__(self, *args, slot: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.slot = slot

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            await _slots.release(self.slot)


async def _request_metas(tenant_id: str, request_ids: list[str]) -> dict[str, dict]:
    if not request_ids:
        return {}
    async def op(tx):
        result = await tx.run(
            "UNWIND $request_ids AS request_id "
            "MATCH (r:Request {tenant_id:$tenant_id, id:request_id}) "
            "RETURN r.id AS id, r.tenant_id AS tenant_id, r.created_by AS created_by, "
            "r.org_ids AS org_ids, r.shared_org_ids AS shared_org_ids, "
            "r.status AS status, r.active_run_id AS active_run_id",
            tenant_id=tenant_id, request_ids=request_ids,
        )
        return {record["id"]: dict(record) for record in await result.data()}
    return await read_tx(tenant_id, op)


async def _request_meta(tenant_id: str, request_id: str) -> dict | None:
    return (await _request_metas(tenant_id, [request_id])).get(request_id)


TENANT_WIDE_KINDS = ("policy.", "rule.")
# Only these payload fields leave the server; payloads never carry source text.
SAFE_PAYLOAD_FIELDS = ("status", "version", "config_version", "rule_id", "rule_version", "candidate_id", "step_name", "kind")
CLASSIFICATION_KEYS = frozenset(OPTIONS)
RISK_KEYS = frozenset({"clinical_safety", "pharmacovigilance", "regulatory"})


def _safe_progress_fields(payload: dict) -> dict:
    safe = {}
    classes = payload.get("classifications")
    if isinstance(classes, dict) and all(
        key in CLASSIFICATION_KEYS and isinstance(value, str) and value in OPTIONS[key]
        for key, value in classes.items()
    ):
        safe["classifications"] = classes
    confidences = payload.get("confidences")
    if isinstance(confidences, dict) and all(
        key in CLASSIFICATION_KEYS and type(value) in (int, float) and 0 <= value <= 1
        for key, value in confidences.items()
    ):
        safe["confidences"] = confidences
    flags = payload.get("risk_flags")
    if isinstance(flags, dict) and all(
        key in RISK_KEYS and isinstance(value, bool) for key, value in flags.items()
    ):
        safe["risk_flags"] = flags
    if isinstance(payload.get("preliminary"), bool):
        safe["preliminary"] = payload["preliminary"]
    for key in ("evidence_count", "task_count"):
        if type(payload.get(key)) is int and payload[key] >= 0:
            safe[key] = payload[key]
    return safe


class _TenantHub:
    """One indexed event scan and one metadata lookup per tenant batch."""

    def __init__(self, tenant_id: str, cursor: int):
        self.tenant_id = tenant_id
        self.cursor = cursor
        self.generation = 0
        self.subscribers: dict[asyncio.Queue, int] = {}
        self.task: asyncio.Task | None = None
        self.listener = TenantSubscriber(tenant_id)

    def subscribe(self, cursor: int) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=32)
        self.subscribers[queue] = cursor
        if cursor < self.cursor:
            self.cursor = cursor
            self.generation += 1
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self.run())
        return queue

    async def run(self) -> None:
        try:
            await self.listener.start()
            while self.subscribers:
                start = self.cursor
                generation = self.generation
                events = await list_events(self.tenant_id, after_seq=start, limit=1000)
                if events:
                    ids = list({item["request_id"] for item in events if item["request_id"]})
                    metas = await _request_metas(self.tenant_id, ids)
                    scanned = events[-1]["seq"]
                    for queue, subscriber_cursor in tuple(self.subscribers.items()):
                        if scanned <= subscriber_cursor:
                            continue
                        try:
                            queue.put_nowait((events, metas, scanned))
                        except asyncio.QueueFull:
                            # A lagging connection must resync from durable state.
                            while not queue.empty():
                                queue.get_nowait()
                            queue.put_nowait(None)
                    if generation == self.generation:
                        self.cursor = scanned
                    await asyncio.sleep(0)
                else:
                    try:
                        await self.listener.wait(5.0 if self.listener.connected else POLL_SECONDS)
                    except TimeoutError:
                        pass  # Backup scan also covers missed Redis notifications.
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - propagate poller failure to each stream
            for queue in tuple(self.subscribers):
                while not queue.empty():
                    queue.get_nowait()
                queue.put_nowait(exc)
        finally:
            await self.listener.close()


async def _subscribe(tenant_id: str, cursor: int) -> tuple[_TenantHub, asyncio.Queue]:
    async with _hubs_lock:
        hub = _hubs.get(tenant_id)
        if hub is None:
            hub = _TenantHub(tenant_id, cursor)
            _hubs[tenant_id] = hub
        return hub, hub.subscribe(cursor)


async def _unsubscribe(hub: _TenantHub, queue: asyncio.Queue) -> None:
    async with _hubs_lock:
        hub.subscribers.pop(queue, None)
        if not hub.subscribers:
            if hub.task:
                hub.task.cancel()
            if _hubs.get(hub.tenant_id) is hub:
                del _hubs[hub.tenant_id]


def _sse(event: str, data: dict, seq: int | None = None) -> bytes:
    fields = []
    if seq is not None:
        fields.append(f"id: {seq}")
    fields.append(f"event: {event}")
    fields.append("data: " + json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    return ("\n".join(fields) + "\n\n").encode()


@router.get("/stream")
async def stream_events(
    request: Request,
    after: int | None = Query(default=None, ge=0),
    max_events: int | None = Query(default=None, ge=1, le=1000),
    principal: Principal = Depends(get_principal),  # noqa: B008
):
    header_id = request.headers.get("last-event-id")
    try:
        # EventSource keeps the URL on automatic reconnect and adds this header.
        # The header represents the last event actually received by the browser.
        cursor = int(header_id) if header_id is not None else (after or 0)
        if cursor < 0:
            raise ValueError
    except ValueError as exc:
        raise HTTPException(400, "Invalid Last-Event-ID") from exc

    slot = await _slots.acquire()
    if slot is None:
        raise HTTPException(503, "SSE connection limit reached")

    async def body():
        nonlocal cursor
        last_heartbeat = time.monotonic()
        last_session_check = last_heartbeat - SESSION_RECHECK_SECONDS
        current_principal = principal
        delivered = 0
        subscription = None
        last_slot_refresh = time.monotonic()
        token = getattr(getattr(request, "state", None), "session_token", None) or request.cookies.get("jev_session")
        try:
            # A cursor ahead of the committed head, or older than the configured recovery
            # window, cannot be trusted to represent a complete client view.
            async def bounds(tx):
                result = await tx.run(
                    "OPTIONAL MATCH (c:EventCounter {tenant_id:$tenant_id}) "
                    "OPTIONAL MATCH (e:Event {tenant_id:$tenant_id}) "
                    "WITH coalesce(c.seq,0) AS head, c.retained_from_seq AS retained_from, "
                    "min(e.created_at) AS oldest "
                    "OPTIONAL MATCH (at_cursor:Event {tenant_id:$tenant_id, seq:$cursor}) "
                    "RETURN head, retained_from, oldest, at_cursor.created_at AS cursor_created",
                    tenant_id=principal.tenant_id, cursor=cursor,
                )
                row = await result.single()
                return row["head"], row["retained_from"], row["oldest"], row["cursor_created"]
            head, retained_from, oldest, cursor_created = await read_tx(principal.tenant_id, bounds)
            reference_time = cursor_created if cursor else oldest
            reference_native = reference_time.to_native() if reference_time else None
            if reference_native and reference_native.tzinfo is None:
                reference_native = reference_native.replace(tzinfo=UTC)
            expired = reference_native and (datetime.now(UTC) - reference_native).total_seconds() > MAX_AFTER_AGE_SECONDS
            # Events below retained_from_seq were removed by retention, so a cursor
            # before it may have missed events the client can no longer replay.
            pruned = retained_from is not None and cursor < retained_from
            if cursor > head or expired or pruned:
                yield _sse("snapshot-required", {"reason": "cursor_out_of_range" if cursor > head else "retention_window"})
                return
            hub, queue = await _subscribe(principal.tenant_id, cursor)
            subscription = (hub, queue)
            while True:
                if time.monotonic() - last_slot_refresh >= 10:
                    await _slots.refresh(slot)
                    last_slot_refresh = time.monotonic()
                if await request.is_disconnected():
                    return
                if token and time.monotonic() - last_session_check >= SESSION_RECHECK_SECONDS:
                    resolved = await session_principal(token)
                    if not resolved or resolved[0].tenant_id != principal.tenant_id:
                        yield _sse("session-expired", {"reason": "session_invalid"})
                        return
                    current_principal = resolved[0]
                    last_session_check = time.monotonic()
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=POLL_SECONDS)
                except TimeoutError:
                    yield b": poll\n\n"
                    message = ()
                if message is None:
                    yield _sse("snapshot-required", {"reason": "subscriber_overflow"})
                    return
                if isinstance(message, Exception):
                    raise message
                if message:
                    batch, metas, scanned_through = message
                    for item in batch:
                        if item["seq"] <= cursor:
                            continue
                        request_id = item["request_id"]
                        audience = item.get("audience")
                        if audience == "tenant":
                            pass
                        elif audience == "request" and not request_id:
                            continue
                        elif request_id:
                            meta = metas.get(request_id)
                            if not meta or not can_view_request(current_principal, meta):
                                continue
                        elif not str(item["kind"]).startswith(TENANT_WIDE_KINDS):
                            continue
                        payload = item["payload"]
                        data = {"request_id": request_id, "run_id": item["run_id"]}
                        data.update({k: payload[k] for k in SAFE_PAYLOAD_FIELDS if k in payload})
                        data.update(_safe_progress_fields(payload))
                        yield _sse(item["kind"], data, item["seq"])
                        now = datetime.now(UTC)
                        created = item["created_at"]
                        await asyncio.to_thread(_journal.append, {"event_id": f"evt_{uuid4().hex}", "attempt_id": f"att_{uuid4().hex}", "request_id": request_id, "run_id": item["run_id"], "tenant_id": principal.tenant_id, "kind": "sse_deliver", "ts": now.isoformat(), "duration_ms": max(0, int((now-created).total_seconds()*1000))})
                        delivered += 1
                        if max_events is not None and delivered >= max_events:
                            return
                    cursor = max(cursor, scanned_through)
                    hub.subscribers[queue] = cursor
                if time.monotonic() - last_heartbeat >= 15:
                    yield b": heartbeat\n\n"
                    last_heartbeat = time.monotonic()
        finally:
            if subscription:
                await _unsubscribe(*subscription)

    return _SlotStreamingResponse(body(), slot=slot, media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/snapshot")
async def event_snapshot(request_id: str, principal: Principal = Depends(get_principal)):  # noqa: B008
    meta = await _request_meta(principal.tenant_id, request_id)
    if not meta or not can_view_request(principal, meta):
        raise HTTPException(404, "Request not found")
    async def query(tx):
        result = await tx.run(
            "MATCH (r:Request {tenant_id:$tenant_id, id:$request_id}) "
            "OPTIONAL MATCH (e:Event {tenant_id:$tenant_id, request_id:$request_id}) "
            "RETURN r.status AS status, r.active_run_id AS active_run_id, coalesce(max(e.seq),0) AS latest_seq",
            tenant_id=principal.tenant_id, request_id=request_id,
        )
        row = await result.single(strict=True)
        return dict(row)
    return {"request_id": request_id, **(await read_tx(principal.tenant_id, query))}
