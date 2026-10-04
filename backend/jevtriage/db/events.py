"""Tenant-local gapless event sequence within committed transactions."""

import json

from jevtriage.db.tx import on_commit, read_tx, write_tx
from jevtriage.domain.ids import new_id
from jevtriage.domain.serialize import json_value, to_native


async def append_event_in_tx(tx, tenant_id: str, kind: str, payload: dict, *, request_id: str | None = None, run_id: str | None = None, audience: str | None = None) -> dict:
    audience = audience or ("tenant" if request_id is None else "request")
    event_id = new_id("event")
    result = await tx.run(
        "MERGE (c:EventCounter {tenant_id: $tenant_id}) "
        "ON CREATE SET c.id = $counter_id, c.seq = 0 "
        "SET c._lock = randomUUID(), c.seq = c.seq + 1 "
        "CREATE (e:Event {id: $event_id, tenant_id: $tenant_id, seq: c.seq, "
        "kind: $kind, payload_json: $payload_json, request_id: $request_id, "
        "run_id: $run_id, audience: $audience, created_at: datetime()}) "
        "RETURN e.id AS id, e.seq AS seq, e.created_at AS created_at",
        tenant_id=tenant_id, counter_id=f"counter_{tenant_id}", event_id=event_id,
        kind=kind, payload_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        request_id=request_id, run_id=run_id, audience=audience,
    )
    record = await result.single(strict=True)
    from jevtriage.realtime.notifier import publish_event
    on_commit(lambda: publish_event(tenant_id, record["seq"]))
    return {"id": record["id"], "seq": record["seq"], "created_at": json_value(record["created_at"])}


async def append_event(tenant_id: str, kind: str, payload: dict, *, request_id: str | None = None, run_id: str | None = None) -> dict:
    return await write_tx(tenant_id, lambda tx: append_event_in_tx(tx, tenant_id, kind, payload, request_id=request_id, run_id=run_id))


async def list_events(tenant_id: str, after_seq: int = 0, limit: int = 100) -> list[dict]:
    if after_seq < 0 or not 1 <= limit <= 1000:
        raise ValueError("invalid event page")

    async def op(tx):
        result = await tx.run(
            "MATCH (e:Event {tenant_id: $tenant_id}) WHERE e.seq > $after_seq "
            "RETURN e.id AS id, e.seq AS seq, e.kind AS kind, e.payload_json AS payload_json, "
            "e.request_id AS request_id, e.run_id AS run_id, e.audience AS audience, e.created_at AS created_at "
            "ORDER BY e.seq LIMIT $limit",
            tenant_id=tenant_id, after_seq=after_seq, limit=limit,
        )
        return [{**dict(record), "payload": json.loads(record["payload_json"]), "created_at": to_native(record["created_at"])} for record in await result.data()]

    return await read_tx(tenant_id, op)
