"""Atomic idempotency reservation and result storage in the caller's transaction."""

import hashlib
import json

from ildongi.db.tx import write_tx
from ildongi.domain.ids import new_id
from ildongi.domain.serialize import dumps


class IdempotencyConflict(ValueError):
    status_code = 409


def payload_hash(payload) -> str:
    """Hash canonical JSON. Verify against each legacy caller's hash before migrating it."""
    return hashlib.sha256(dumps(payload).encode()).hexdigest()


async def get_or_create_in_tx(tx, tenant_id: str, scope: str, key: str, payload_hash: str, create_result):
    if not scope or not key or not payload_hash:
        raise ValueError("scope, key and payload_hash required")
    result = await tx.run(
        "MERGE (i:Idempotency {tenant_id: $tenant_id, scope: $scope, key: $key}) "
        "ON CREATE SET i.id = $id, i.payload_hash = $payload_hash, i.created_at = datetime() "
        "SET i._lock = randomUUID() "
        "RETURN i.payload_hash AS payload_hash, i.result_json AS result_json",
        tenant_id=tenant_id, scope=scope, key=key, id=new_id("idempotency"), payload_hash=payload_hash,
    )
    record = await result.single(strict=True)
    if record["payload_hash"] != payload_hash:
        raise IdempotencyConflict("idempotency key reused with different payload")
    if record["result_json"] is not None:
        return json.loads(record["result_json"])
    value = await create_result(tx)
    await (await tx.run(
        "MATCH (i:Idempotency {tenant_id: $tenant_id, scope: $scope, key: $key}) "
        "SET i.result_json = $result_json",
        tenant_id=tenant_id, scope=scope, key=key,
        result_json=dumps(value),
    )).consume()
    return value


async def get_or_create(tenant_id: str, scope: str, key: str, payload_hash: str, create_result):
    return await write_tx(tenant_id, lambda tx: get_or_create_in_tx(tx, tenant_id, scope, key, payload_hash, create_result))


async def idempotent_write(tenant_id: str, scope: str, key: str, payload, create_fn):
    """Run a payload-hashed idempotent write; conflicts propagate unchanged."""
    digest = payload_hash(payload)
    return await write_tx(tenant_id, lambda tx: get_or_create_in_tx(
        tx, tenant_id, scope, key, digest, create_fn))
