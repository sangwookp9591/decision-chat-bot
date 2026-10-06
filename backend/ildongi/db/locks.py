"""Acquire write locks in Request -> Run -> Review -> Assignment -> Job order."""

from neo4j import AsyncTransaction

LOCK_ORDER = ("Request", "Run", "Review", "Assignment", "Job")


class NodeNotFound(LookupError):
    pass


async def lock_node_in_tx(tx: AsyncTransaction, tenant_id: str, label: str, node_id: str):
    if label not in LOCK_ORDER:
        raise ValueError("unsupported lock label")
    result = await tx.run(
        f"MATCH (n:{label} {{tenant_id: $tenant_id, id: $node_id}}) "
        "SET n._lock = randomUUID() RETURN n",
        tenant_id=tenant_id, node_id=node_id,
    )
    record = await result.single()
    if record is None:
        raise NodeNotFound(f"{label} {node_id}")
    return record["n"]


async def lock_nodes_in_tx(tx: AsyncTransaction, tenant_id: str, nodes: list[tuple[str, str]]):
    if nodes != sorted(nodes, key=lambda item: (LOCK_ORDER.index(item[0]), item[1])):
        raise ValueError("locks must be acquired in canonical order")
    return [await lock_node_in_tx(tx, tenant_id, label, node_id) for label, node_id in nodes]
