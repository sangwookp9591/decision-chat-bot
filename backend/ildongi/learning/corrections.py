"""Read-only, tenant-scoped Correction comparison queries."""
from __future__ import annotations

import json
from typing import Any

from ildongi.db.tx import read_tx


def _decode(row: dict[str, Any]) -> dict[str, Any]:
    value = dict(row["c"])
    for key in ("ai_value", "corrected_value", "evidence_span_ids"):
        raw = value.get(key)
        if raw is not None:
            try:
                value[key] = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                pass
    for key in ("corrected_at", "created_at"):
        if value.get(key) is not None:
            value[key] = str(value[key])
    value["review_decision_id"] = row.get("decision_id")
    value["review_action"] = row.get("action")
    return value


async def list_corrections(tenant: str, *, field: str | None = None,
                           request_id: str | None = None, from_: str | None = None,
                           to: str | None = None, limit: int = 500) -> list[dict]:
    async def op(tx):
        rows = await (await tx.run(
            "MATCH (h:ReviewDecision {tenant_id:$tenant})-[:RECORDED]->(c:Correction {tenant_id:$tenant}) "
            "WHERE ($field IS NULL OR c.field=$field) AND ($request IS NULL OR c.request_id=$request) "
            "AND ($from_ IS NULL OR toString(c.corrected_at)>=$from_) "
            "AND ($to IS NULL OR toString(c.corrected_at)<=$to) "
            "RETURN c,h.id AS decision_id,h.action AS action "
            "ORDER BY c.corrected_at DESC LIMIT $limit",
            tenant=tenant, field=field, request=request_id, from_=from_, to=to, limit=limit,
        )).data()
        return [_decode(row) for row in rows]
    return await read_tx(tenant, op)


async def get_request_corrections(tenant: str, request_id: str) -> list[dict]:
    return await list_corrections(tenant, request_id=request_id)
