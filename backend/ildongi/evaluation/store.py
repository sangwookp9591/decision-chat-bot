"""Persistence for human evaluation labels and audit events."""

import json
from typing import Any

from ildongi.db.tx import read_tx, write_tx


async def labels_for_split(tenant: str, split: str) -> list[dict[str, Any]]:
    async def op(tx):
        result = await tx.run(
            "MATCH (l:EvalLabel {tenant_id:$tenant,split:$split}) "
            "RETURN l.sample_id AS id,l.labels AS labels,l.status AS status,l.user_id AS user_id,"
            "l.reason AS reason,l.confidence AS confidence,l.created_at AS created_at "
            "ORDER BY l.created_at", tenant=tenant, split=split)
        return await result.data()
    return await read_tx(tenant, op)


async def record_label(tenant: str, split: str, sample_id: str, user_id: str,
                       labels: dict[str, Any], status: str, reason: str | None,
                       confidence: float, action: str) -> None:
    async def op(tx):
        await (await tx.run(
            "CREATE (l:EvalLabel {tenant_id:$tenant,split:$split,sample_id:$id,user_id:$user,"
            "labels:$labels,status:$status,reason:$reason,confidence:$confidence,created_at:datetime()}) "
            "CREATE (a:AuditEvent {tenant_id:$tenant,kind:'evaluation_label',actor:$user,"
            "subject:$id,action:$action,reason:$reason,created_at:datetime()})",
            tenant=tenant, split=split, id=sample_id, user=user_id,
            labels=json.dumps(labels, ensure_ascii=False), status=status,
            reason=reason, confidence=confidence, action=action)).consume()
    await write_tx(tenant, op)
