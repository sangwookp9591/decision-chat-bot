"""Tenant scoped, read-only queries over the stored judgment relationships.

Only relationships that exist in Neo4j are returned; nothing is inferred or joined across
missing links. Authorization of request-bound nodes is applied by the caller through the
``visible`` callback so that hidden nodes are never traversed or counted.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from jevtriage.db.tx import read_tx
from jevtriage.domain.serialize import json_value
from jevtriage.graph.model import (
    EDGE_TYPES,
    FORWARD_UP_TYPES,
    KIND_LAYER,
    KINDS,
    LAYERS,
    MAX_DEPTH,
    NODE_CAP,
    UP_TYPE_PATTERN,
    decode_value,
    describe,
    edge_id,
)

Visible = Callable[[str | None], Awaitable[bool]]
ALL_TYPES = "|".join(EDGE_TYPES)
STATEFUL = ("RuleCandidate", "RuleVersion", "ValidationRun", "ConfigVersion")
_REF_KEYS = {"run_id": "run_id", "review_id": "review_id", "revision_id": "revision_id"}


def _iso(value: Any) -> Any:
    return json_value(value)


def node_record(kind: str, props: dict[str, Any], request_id: str | None) -> dict[str, Any]:
    props = {k: _iso(v) for k, v in props.items()}
    info = describe(kind, props)
    refs: dict[str, Any] = {k: props[k] for k in _REF_KEYS if props.get(k) is not None}
    if request_id:
        refs["request_id"] = request_id
    if kind == "EvidenceSpan":
        refs.update(span_id=props["id"], source=props.get("attachment_id") or "chat")
    if kind == "RunStep":
        refs["step_id"] = props["id"]
    if kind == "RuleVersion":
        refs.update(rule_id=props.get("rule_id"), rule_version=props["id"])
    if kind == "ConfigVersion":
        refs["config_version"] = props.get("version")
    elif kind == "Correction" and props.get("config_version") is not None:
        refs["config_version"] = props["config_version"]
    if kind == "RuleCandidate":
        refs["candidate_id"] = props["id"]
    return {"id": props["id"], "kind": kind, "layer": KIND_LAYER[kind], "request_id": request_id,
            "refs": refs, **info}


async def resolve_node(tenant: str, node_id: str, kind: str | None = None):
    kinds = [kind] if kind in KINDS else list(KINDS)

    async def op(tx):
        for label in kinds:
            rows = await (await tx.run(
                f"MATCH (n:{label} {{tenant_id:$tenant,id:$id}}) "
                "OPTIONAL MATCH (r:Run {tenant_id:$tenant,id:n.run_id}) "
                "RETURN labels(n) AS labels,properties(n) AS p,"
                "coalesce(n.request_id,r.request_id) AS request_id",
                tenant=tenant, id=node_id)).data()
            for row in rows:
                if label in row["labels"]:
                    return label, dict(row["p"]), row["request_id"]
        return None
    return await read_tx(tenant, op)


async def _seed_rows(tx, tenant: str, *, request_id, run_id, rule_id, config_version, status, limit):
    ids: set[str] = set()

    async def add(cypher: str, **params):
        for row in await (await tx.run(cypher, tenant=tenant, **params)).data():
            ids.add(row["e"])

    selected = False
    if request_id or run_id:
        selected = True
        params = {"req": request_id, "run": run_id}
        scope = "($req IS NULL OR r.request_id=$req) AND ($run IS NULL OR r.id=$run)"
        await add("MATCH (r:Run {tenant_id:$tenant}) WHERE " + scope +
                  " MATCH (r)-[:PRODUCED]->(:Judgment)<-[:OF_JUDGMENT]-(n:ModelOutput) RETURN elementId(n) AS e", **params)
        await add("MATCH (r:Run {tenant_id:$tenant}) WHERE " + scope +
                  " MATCH (r)-[:HAS_STEP]->(n:RunStep) WHERE (n)-[:USED_OUTPUT|APPLIED]->() RETURN elementId(n) AS e", **params)
        for label in ("Correction", "ReviewDecision"):
            await add(f"MATCH (n:{label} {{tenant_id:$tenant}}) WHERE ($req IS NULL OR n.request_id=$req) "
                      "AND ($run IS NULL OR n.run_id=$run) RETURN elementId(n) AS e", **params)
    if rule_id:
        selected = True
        match = "n.id=$rule" if "@" in rule_id else "n.rule_id=$rule"
        await add(f"MATCH (n:RuleVersion {{tenant_id:$tenant}}) WHERE {match} RETURN elementId(n) AS e", rule=rule_id)
    if config_version is not None:
        selected = True
        await add("MATCH (n:ConfigVersion {tenant_id:$tenant,version:$v}) RETURN elementId(n) AS e", v=config_version)
    if not selected and status:
        selected = True
        for label in STATEFUL:
            await add(f"MATCH (n:{label} {{tenant_id:$tenant}}) WHERE n.status=$s RETURN elementId(n) AS e LIMIT $n",
                      s=status, n=limit)
    if not selected:  # overview: most recent stored records only
        for label in ("Correction", "RuleCandidate", "RuleVersion", "ReviewDecision"):
            await add(f"MATCH (n:{label} {{tenant_id:$tenant}}) RETURN elementId(n) AS e "
                      "ORDER BY coalesce(n.created_at,n.decided_at) DESC LIMIT $n", n=limit)
    return ids


_NEIGHBOR = {
    "up": (f"MATCH (a)-[r:{UP_TYPE_PATTERN}]->(b)", f"MATCH (a)<-[r:{'|'.join(FORWARD_UP_TYPES)}]-(b)"),
    "down": (f"MATCH (a)<-[r:{UP_TYPE_PATTERN}]-(b)", f"MATCH (a)-[r:{'|'.join(FORWARD_UP_TYPES)}]->(b)"),
}
_KIND_FILTER = " WHERE elementId(a) IN $ids AND a.tenant_id=$tenant AND b.tenant_id=$tenant AND any(l IN labels(b) WHERE l IN $kinds)"
# Neighbours fetched per expansion step, relative to the remaining node budget (visibility
# and status filtering happen after the read, so some headroom keeps results stable).
_EXPAND_HEADROOM = 4
_NODE_RETURN = (" OPTIONAL MATCH (run:Run {tenant_id:$tenant,id:b.run_id}) "
                "RETURN DISTINCT elementId(b) AS e, labels(b) AS labels, properties(b) AS p, "
                "coalesce(b.request_id,run.request_id) AS request_id")


async def _nodes_by_eid(tx, tenant: str, eids: list[str]) -> dict[str, dict]:
    rows = await (await tx.run(
        "MATCH (b) WHERE elementId(b) IN $ids AND b.tenant_id=$tenant AND any(l IN labels(b) WHERE l IN $kinds)" + _NODE_RETURN,
        tenant=tenant, ids=eids, kinds=list(KINDS))).data()
    return {r["e"]: _row_node(r) for r in rows}


def _row_node(row: dict) -> dict:
    kind = next(label for label in row["labels"] if label in KIND_LAYER)
    return node_record(kind, dict(row["p"]), row["request_id"])


async def collect(tenant: str, visible: Visible, *, request_id=None, run_id=None, rule_id=None,
                  config_version=None, status=None, depth=6, cap=NODE_CAP, preload=None) -> dict[str, Any]:
    depth = max(1, min(depth, MAX_DEPTH))
    cap = max(1, min(cap, NODE_CAP))
    seeds = await read_tx(tenant, lambda tx: _seed_rows(
        tx, tenant, request_id=request_id, run_id=run_id, rule_id=rule_id,
        config_version=config_version, status=status, limit=40))
    nodes: dict[str, dict] = {}
    truncated = False

    async def admit(eid: str, record: dict) -> bool:
        if eid in nodes:
            return True
        if status and record["kind"] in STATEFUL and (request_id or run_id or rule_id or config_version is not None) \
                and record.get("status") != status:
            return False
        if not await visible(record["request_id"]):
            return False
        if len(nodes) >= cap:
            return False
        nodes[eid] = record
        return True

    async def seed_nodes(tx):
        return await _nodes_by_eid(tx, tenant, sorted(seeds))
    seed_records = await read_tx(tenant, seed_nodes) if seeds else {}
    if preload:
        await preload(record["request_id"] for record in seed_records.values())
    for eid, record in seed_records.items():
        if not await admit(eid, record):
            truncated = truncated or len(nodes) >= cap
    seed_eids = list(nodes)  # each direction expands monotonically from the seeds only
    for direction in ("up", "down"):
        frontier = list(seed_eids)
        for _ in range(depth):
            if not frontier:
                break
            found: dict[str, dict] = {}

            # Bound the read in the database, not after it: a hub node (e.g. a ConfigVersion every Run
            # points at) would otherwise load its whole neighbourhood before the cap is applied.
            room = max(cap - len(nodes), 0)
            if room == 0:
                truncated = True
                break
            limit = room * _EXPAND_HEADROOM + len(frontier)

            async def expand(tx, frontier=frontier, found=found, direction=direction, limit=limit):
                hit = False
                for pattern in _NEIGHBOR[direction]:
                    rows = await (await tx.run(pattern + _KIND_FILTER + _NODE_RETURN + " LIMIT $limit",
                                               tenant=tenant, ids=frontier, kinds=list(KINDS),
                                               limit=limit)).data()
                    hit = hit or len(rows) >= limit
                    for row in rows:
                        found[row["e"]] = _row_node(row)
                return hit
            if await read_tx(tenant, expand):
                truncated = True
            if preload:
                await preload(record["request_id"] for record in found.values())
            nxt: list[str] = []
            for eid, record in found.items():
                if eid in nodes:
                    continue
                if await admit(eid, record):
                    nxt.append(eid)
                else:
                    truncated = truncated or len(nodes) >= cap
            frontier = nxt
    edges = await _induced_edges(tenant, nodes)
    return assemble(nodes, edges, truncated)


async def _induced_edges(tenant: str, nodes: dict[str, dict]) -> list[dict]:
    if not nodes:
        return []
    eids = list(nodes)

    async def op(tx):
        return await (await tx.run(
            f"MATCH (a)-[r:{ALL_TYPES}]->(b) WHERE elementId(a) IN $ids AND elementId(b) IN $ids "
            "AND a.tenant_id=$tenant AND b.tenant_id=$tenant "
            "RETURN elementId(a) AS a, elementId(b) AS b, type(r) AS type, properties(r) AS p",
            ids=eids, tenant=tenant)).data()
    rows = await read_tx(tenant, op)
    edges = []
    for row in rows:
        source, target = nodes[row["a"]], nodes[row["b"]]
        props = {k: decode_value(_iso(v)) for k, v in dict(row["p"]).items()}
        up, down = (source, target) if row["type"] in FORWARD_UP_TYPES else (target, source)
        edges.append({"id": edge_id(row["type"], source["id"], target["id"]), "type": row["type"],
                      "source": source["id"], "target": target["id"],
                      "upstream": up["id"], "downstream": down["id"], "props": props})
    return sorted(edges, key=lambda e: e["id"])


def assemble(nodes: dict[str, dict], edges: list[dict], truncated: bool) -> dict[str, Any]:
    records = sorted(nodes.values(), key=lambda n: (n["layer"], n["kind"], n["id"]))
    up_count = {n["id"]: 0 for n in records}
    down_count = dict(up_count)
    for e in edges:
        down_count[e["upstream"]] += 1
        up_count[e["downstream"]] += 1
    for n in records:
        n["upstream_count"], n["downstream_count"] = up_count[n["id"]], down_count[n["id"]]
    layers = [{"layer": i, **meta, "count": sum(1 for n in records if n["layer"] == i)}
              for i, meta in LAYERS.items()]
    return {"nodes": records, "edges": edges, "layers": layers, "truncated": truncated,
            "node_count": len(records), "edge_count": len(edges)}


async def trace(tenant: str, kind: str, node_id: str, direction: str, depth: int, limit: int):
    """Quantified path pattern traversal along stored relationships only."""
    depth = max(1, min(depth, MAX_DEPTH))
    up = f"((a {{tenant_id:$tenant}})-[:{UP_TYPE_PATTERN}]->(b {{tenant_id:$tenant}}))"
    down = f"((a {{tenant_id:$tenant}})<-[:{UP_TYPE_PATTERN}]-(b {{tenant_id:$tenant}}))"
    origin = f"(n:{kind} {{tenant_id:$tenant,id:$id}})"
    tail = ("RETURN [x IN nodes(p) | [labels(x)[0], x.id]] AS nodes, "
            "[r IN relationships(p) | [type(r), startNode(r).id, endNode(r).id]] AS rels LIMIT $limit")
    queries: dict[str, list[str]] = {"up": [], "down": []}
    queries["up"].append(f"MATCH p = {origin} {up}{{1,{depth}}} (m) {tail}")
    queries["down"].append(f"MATCH p = {origin} {down}{{1,{depth}}} (m) {tail}")
    if kind == "ConfigVersion":
        queries["up"].append(
            f"MATCH p = {origin}<-[:PUBLISHED_IN]-(rv:RuleVersion {{tenant_id:$tenant}}) {up}{{0,{depth - 1}}} (m) {tail}")
    queries["down"].append(
        f"MATCH p = {origin} {down}{{0,{depth - 1}}} (rv:RuleVersion {{tenant_id:$tenant}})"
        f"-[:PUBLISHED_IN]->(cv:ConfigVersion {{tenant_id:$tenant}}) {tail}")
    wanted = ("up", "down") if direction == "both" else (direction,)
    raw: list[tuple[str, list, list]] = []

    async def op(tx):
        for d in wanted:
            for cypher in queries[d]:
                for row in await (await tx.run(cypher, tenant=tenant, id=node_id, limit=limit * 5)).data():
                    raw.append((d, row["nodes"], row["rels"]))
    await read_tx(tenant, op)
    return raw


def maximal(paths: list[tuple[str, list, list]]) -> list[tuple[str, list, list]]:
    """Drop paths that are strict prefixes of another path in the same direction."""
    keys = {(d, tuple(tuple(n) for n in nodes)) for d, nodes, _ in paths}
    out, seen = [], set()
    for d, nodes, rels in paths:
        key = (d, tuple(tuple(n) for n in nodes))
        if key in seen:
            continue
        seen.add(key)
        if any(o[0] == d and len(o[1]) > len(key[1]) and o[1][: len(key[1])] == key[1] for o in keys):
            continue
        out.append((d, nodes, rels))
    return out


async def hydrate(tenant: str, pairs: set[tuple[str, str]]) -> dict[tuple[str, str], dict]:
    by_kind: dict[str, list[str]] = {}
    for kind, nid in pairs:
        by_kind.setdefault(kind, []).append(nid)

    async def op(tx):
        out = {}
        for kind, ids in by_kind.items():
            rows = await (await tx.run(
                f"MATCH (b:{kind} {{tenant_id:$tenant}}) WHERE b.id IN $ids "
                "OPTIONAL MATCH (run:Run {tenant_id:$tenant,id:b.run_id}) "
                "RETURN labels(b) AS labels, properties(b) AS p, coalesce(b.request_id,run.request_id) AS request_id",
                tenant=tenant, ids=ids)).data()
            for row in rows:
                record = _row_node(row)
                out[(record["kind"], record["id"])] = record
        return out
    return await read_tx(tenant, op)


def edge_from_rel(rel: list, nodes: dict[tuple[str, str], dict]) -> dict:
    type_, source, target = rel
    up, down = (source, target) if type_ in FORWARD_UP_TYPES else (target, source)
    return {"id": edge_id(type_, source, target), "type": type_, "source": source, "target": target,
            "upstream": up, "downstream": down}


async def edge_props(tenant: str, edges: dict[str, dict], nodes: dict[tuple[str, str], dict]) -> None:
    if not edges:
        return
    kind_of = {nid: kind for kind, nid in nodes}
    ids = [(e["type"], e["source"], e["target"], kind_of[e["source"]], kind_of[e["target"]])
           for e in edges.values()]

    async def op(tx):
        rows = []
        for source_kind, target_kind in {(sk, tk) for _, _, _, sk, tk in ids}:
            pair_edges = [{"type": typ, "source": source, "target": target}
                          for typ, source, target, sk, tk in ids
                          if (sk, tk) == (source_kind, target_kind)]
            rows.extend(await (await tx.run(
                f"UNWIND $edges AS e MATCH (a:{source_kind} {{tenant_id:$tenant,id:e.source}})"
                f"-[r]->(b:{target_kind} {{tenant_id:$tenant,id:e.target}}) "
                "WHERE type(r)=e.type "
                "RETURN e.type AS type,e.source AS source,e.target AS target,properties(r) AS p",
                tenant=tenant, edges=pair_edges)).data())
        out = {edge_id(row["type"], row["source"], row["target"]):
               {k: decode_value(_iso(v)) for k, v in dict(row["p"]).items()} for row in rows}
        for type_, source, target, *_ in ids:
            out.setdefault(edge_id(type_, source, target), {})
        return out
    props = await read_tx(tenant, op)
    for key, value in props.items():
        edges[key]["props"] = value


def reachable(paths: list[tuple[str, list, list]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {"up": set(), "down": set()}
    for d, nodes, _ in paths:
        result[d].update(n[1] for n in nodes[1:])
    return result
async def request_metas(tenant: str, ids: list[str]) -> list[dict]:
    async def op(tx):
        return await (await tx.run(
            "UNWIND $ids AS id OPTIONAL MATCH (r:Request {tenant_id:$tenant,id:id}) "
            "RETURN id,properties(r) AS meta",
            tenant=tenant, ids=ids,
        )).data()

    return await read_tx(tenant, op)
