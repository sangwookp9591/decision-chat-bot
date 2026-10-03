"""Immutable audit record creation inside business transactions."""

import json

from jevtriage.domain.ids import new_id


async def append_audit_in_tx(tx, tenant_id: str, actor_id: str, action: str, target_type: str, target_id: str, before: dict | None, after: dict | None, reason: str) -> str:
    if not all((tenant_id, actor_id, action, target_type, target_id, reason)):
        raise ValueError("audit identity, action, target and reason required")
    audit_id = new_id("audit")
    await (await tx.run(
        "CREATE (a:Audit {id: $id, tenant_id: $tenant_id, actor_id: $actor_id, "
        "action: $action, target_type: $target_type, target_id: $target_id, "
        "before_json: $before_json, after_json: $after_json, reason: $reason, created_at: datetime()})",
        id=audit_id, tenant_id=tenant_id, actor_id=actor_id, action=action,
        target_type=target_type, target_id=target_id,
        before_json=json.dumps(before, ensure_ascii=False) if before is not None else None,
        after_json=json.dumps(after, ensure_ascii=False) if after is not None else None, reason=reason,
    )).consume()
    return audit_id
