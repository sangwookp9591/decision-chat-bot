"""A hub node must not load its whole neighbourhood before the node cap applies."""
from __future__ import annotations

from uuid import uuid4

import pytest

from ildongi.db.schema import apply_schema
from ildongi.db.tx import write_tx
from ildongi.graph import query

pytestmark = pytest.mark.asyncio(loop_scope="session")

FANOUT = 300


async def test_hub_expansion_reads_are_bounded_by_cap(monkeypatch):
    tenant = f"graph_hub_{uuid4().hex[:10]}"
    await apply_schema()

    async def seed(tx):
        await (await tx.run(
            "CREATE (cfg:ConfigVersion {id:$cfg, tenant_id:$tenant, version:9, status:'active', created_at:datetime()}) "
            "WITH cfg UNWIND range(1, $n) AS i "
            "CREATE (:RuleVersion {id:'rv_' + toString(i), tenant_id:$tenant, rule_id:'R-HUB', version:i, "
            "status:'published', created_at:datetime()})-[:PUBLISHED_IN]->(cfg)",
            cfg=f"cfg_{tenant}", tenant=tenant, n=FANOUT)).consume()
    await write_tx(tenant, seed)

    materialized = 0
    original = query._row_node

    def counting(row):
        nonlocal materialized
        materialized += 1
        return original(row)
    monkeypatch.setattr(query, "_row_node", counting)

    async def visible(_request_id):
        return True
    try:
        graph = await query.collect(tenant, visible, config_version=9, cap=20)
        assert len(graph["nodes"]) <= 20
        assert graph["truncated"] is True
        assert materialized < FANOUT // 2, materialized
    finally:
        await write_tx(tenant, lambda tx: tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=tenant))
