"""A shared Neo4j database must keep tenant reads separated."""

from uuid import uuid4

import pytest

from ildongi.db.tx import cross_tenant_tx, read_tx, write_tx


@pytest.mark.asyncio
async def test_same_node_id_is_scoped_to_transaction_tenant():
    node_id = f"tenant_tx_{uuid4().hex}"
    tenants = (f"tenant_a_{uuid4().hex}", f"tenant_b_{uuid4().hex}")

    async def create(tx):
        await (await tx.run(
            "CREATE (:TenantTxProbe {id:$id,tenant_id:$tenant_id})", id=node_id,
        )).consume()

    async def count(tx):
        row = await (await tx.run(
            "MATCH (n:TenantTxProbe {id:$id,tenant_id:$tenant_id}) RETURN count(n) AS n",
            id=node_id,
        )).single(strict=True)
        return row["n"]

    async def cleanup(tx):
        await (await tx.run("MATCH (n:TenantTxProbe {id:$id}) DETACH DELETE n", id=node_id)).consume()

    try:
        await write_tx(tenants[0], create)
        assert await read_tx(tenants[0], count) == 1
        assert await read_tx(tenants[1], count) == 0
        await write_tx(tenants[1], create)
        assert await read_tx(tenants[0], count) == 1
        assert await read_tx(tenants[1], count) == 1
        with pytest.raises(ValueError, match="tenant"):
            await read_tx(tenants[0], lambda tx: tx.run("MATCH (n:TenantTxProbe) RETURN n"))
    finally:
        await cross_tenant_tx("tenant-tx-test-cleanup", cleanup, write=True)
