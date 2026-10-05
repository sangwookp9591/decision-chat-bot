"""Judgment graph and path queries (T29). Read-only; tenant and request scope enforced."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from jevtriage.auth.core import Principal, get_principal
from jevtriage.auth.policy import can, redact_source
from jevtriage.domain.api_types import Int64
from jevtriage.graph import query
from jevtriage.graph.model import KINDS, MAX_DEPTH
from jevtriage.ingest.service import request_meta as get_request_meta

router = APIRouter(prefix="/api/graph", tags=["graph"])


def _guard(principal: Principal) -> None:
    if not can(principal, "view_graph", {"tenant_id": principal.tenant_id}):
        raise HTTPException(403, "Insufficient role")


class Scope:
    """Caches per-request readability so hidden nodes are never traversed or counted."""

    def __init__(self, principal: Principal):
        self.principal, self.cache = principal, {}

    async def visible(self, request_id: str | None) -> bool:
        if request_id is None:
            return True  # tenant-wide rule lifecycle nodes; role already checked
        if request_id not in self.cache:
            meta = await get_request_meta(self.principal.tenant_id, request_id)
            self.cache[request_id] = bool(meta and can(self.principal, "view_graph", meta))
        return self.cache[request_id]

    async def preload(self, request_ids) -> None:
        ids = list({request_id for request_id in request_ids if request_id is not None and request_id not in self.cache})
        if not ids:
            return
        for row in await query.request_metas(self.principal.tenant_id, ids):
            self.cache[row["id"]] = bool(row["meta"] and can(self.principal, "view_graph", row["meta"]))


@router.get("/judgment")
async def judgment_graph(request_id: str | None = None, run_id: str | None = None,
                         rule_id: str | None = None, config_version: Int64 | None = None,
                         status: str | None = None,
                         depth: int = Query(6, ge=1, le=MAX_DEPTH),
                         principal: Principal = Depends(get_principal)):  # noqa: B008
    _guard(principal)
    scope = Scope(principal)
    if request_id and not await scope.visible(request_id):
        raise HTTPException(404, "Request not found")
    result = await query.collect(principal.tenant_id, scope.visible, preload=scope.preload, request_id=request_id,
                                 run_id=run_id, rule_id=rule_id, config_version=config_version,
                                 status=status, depth=depth)
    result["criteria"] = {"request_id": request_id, "run_id": run_id, "rule_id": rule_id,
                          "config_version": config_version, "status": status, "depth": depth}
    return redact_source(principal, result)


async def _visible_paths(principal: Principal, scope: Scope, raw, nodes_by_key):
    keep = []
    await scope.preload(record["request_id"] for record in nodes_by_key.values())
    for item in raw:
        keys = [tuple(key) for key in item[1]]
        shown = True
        for key in keys:
            if key not in nodes_by_key or not await scope.visible(nodes_by_key[key]["request_id"]):
                shown = False
                break
        if shown:
            keep.append(item)
    return keep


async def _trace(principal: Principal, scope: Scope, kind: str, node_id: str, direction: str,
                 depth: int, limit: int):
    raw = query.maximal(await query.trace(principal.tenant_id, kind, node_id, direction, depth, limit))
    pairs = {tuple(n) for _, nodes, _ in raw for n in nodes}
    nodes_by_key = await query.hydrate(principal.tenant_id, pairs)
    return await _visible_paths(principal, scope, raw, nodes_by_key), nodes_by_key


@router.get("/judgment/path")
async def judgment_path(node_id: str, direction: str = Query("both", pattern="^(up|down|both)$"),
                        kind: str | None = None, depth: int = Query(6, ge=1, le=MAX_DEPTH),
                        limit: int = Query(100, ge=1, le=500),
                        principal: Principal = Depends(get_principal)):  # noqa: B008
    _guard(principal)
    found = await query.resolve_node(principal.tenant_id, node_id, kind)
    scope = Scope(principal)
    if not found or not await scope.visible(found[2]):
        raise HTTPException(404, "Node not found")
    origin_kind = found[0]
    paths, nodes_by_key = await _trace(principal, scope, origin_kind, node_id, direction, depth, limit)
    truncated = len(paths) > limit
    paths = paths[:limit]
    edges: dict[str, dict] = {}
    for _, _, rels in paths:
        for rel in rels:
            edge = query.edge_from_rel(rel, nodes_by_key)
            edges[edge["id"]] = edge
    await query.edge_props(principal.tenant_id, edges, nodes_by_key)
    used = {tuple(n) for _, nodes, _ in paths for n in nodes}
    reach = query.reachable(paths)
    return redact_source(principal, {"origin": {"id": node_id, "kind": origin_kind}, "direction": direction, "depth": depth,
            "limit": limit, "truncated": truncated,
            "paths": [{"direction": d, "node_ids": [n[1] for n in nodes],
                       "edge_ids": [query.edge_from_rel(r, nodes_by_key)["id"] for r in rels]}
                      for d, nodes, rels in paths],
            "nodes": sorted((nodes_by_key[k] for k in used), key=lambda n: (n["layer"], n["id"])),
            "edges": sorted(edges.values(), key=lambda e: e["id"]),
            "upstream_ids": sorted(reach["up"]), "downstream_ids": sorted(reach["down"])})


@router.get("/judgment/nodes/{node_id}")
async def judgment_node(node_id: str, kind: str | None = None,
                        principal: Principal = Depends(get_principal)):  # noqa: B008
    _guard(principal)
    if kind is not None and kind not in KINDS:
        raise HTTPException(422, "Unknown node kind")
    found = await query.resolve_node(principal.tenant_id, node_id, kind)
    scope = Scope(principal)
    if not found or not await scope.visible(found[2]):
        raise HTTPException(404, "Node not found")
    label, props, request_id = found
    record = query.node_record(label, props, request_id)
    paths, nodes_by_key = await _trace(principal, scope, label, node_id, "both", MAX_DEPTH, 500)
    reach = query.reachable(paths)
    direct: dict[str, list[dict]] = {"up": [], "down": []}
    edges: dict[str, dict] = {}
    seen: set[tuple[str, str]] = set()
    for d, nodes, rels in paths:  # first hop of every maximal path is a direct neighbor
        if (d, nodes[1][1]) in seen:
            continue
        seen.add((d, nodes[1][1]))
        neighbor = nodes_by_key[tuple(nodes[1])]
        direct[d].append({"id": neighbor["id"], "kind": neighbor["kind"], "layer": neighbor["layer"],
                          "title": neighbor["title"]})
        edge = query.edge_from_rel(rels[0], nodes_by_key)
        edges[edge["id"]] = edge
    await query.edge_props(principal.tenant_id, edges, nodes_by_key)
    record.update(upstream_count=len(reach["up"]), downstream_count=len(reach["down"]),
                  upstream=direct["up"], downstream=direct["down"],
                  edges=sorted(edges.values(), key=lambda e: e["id"]),
                  can_read_source=bool(principal.can_read_source), source_link=None)
    if label == "EvidenceSpan" and request_id and principal.can_read_source:
        record["source_link"] = f"/api/requests/{request_id}/evidence/{node_id}"
    return redact_source(principal, record)
