"""Read-only execution flow projections."""

from jevtriage.db.tx import read_tx
from jevtriage.domain.serialize import json_value


async def get_flow(tenant_id: str, run_id: str):
    async def op(tx):
        row = await (await tx.run(
            "MATCH (r:Run {tenant_id:$tenant_id,id:$run_id}) "
            "OPTIONAL MATCH (r)-[:HAS_STEP]->(s:RunStep {tenant_id:$tenant_id}) "
            "OPTIONAL MATCH (v:Review {tenant_id:$tenant_id,request_id:r.request_id,run_id:r.id}) "
            "OPTIONAL MATCH (v)-[:HAS_DECISION]->(d:ReviewDecision {tenant_id:$tenant_id}) "
            "RETURN r,collect(DISTINCT s) AS steps,collect(DISTINCT {review:v,decision:d}) AS reviews",
            tenant_id=tenant_id, run_id=run_id,
        )).single()
        if not row:
            return None
        steps = [dict(s) for s in row["steps"] if s]
        reviews = [dict(v) for v in row["reviews"] if v and v.get("review")]
        nodes, edges = [], []
        ids = {s["id"] for s in steps}
        for s in steps:
            nodes.append({**s, "actor_kind": s.get("actor") if s.get("actor") in {"ai", "code", "rule", "external", "human"} else s.get("kind"), "attempt": s.get("attempt_id"), "versions": _json_field(s.get("versions_json")), "input_summary": _json_field(s.get("input_summary_json")), "output_summary": _json_field(s.get("output_summary_json"))})
            for pred in s.get("predecessor_ids", []):
                if pred in ids: edges.append({"from": pred, "to": s["id"], "kind": "predecessor"})
            parent = s.get("parent_step_id")
            if parent in ids and not any(e["from"] == parent and e["to"] == s["id"] for e in edges):
                edges.append({"from": parent, "to": s["id"], "kind": "parent"})
        for item in reviews:
            review, decision = dict(item["review"]), item.get("decision")
            ended_at = (decision.get("decided_at") or decision.get("created_at")) if decision else None
            duration_ms = max(0, int((ended_at.to_native() - review["created_at"].to_native()).total_seconds() * 1000)) if ended_at and review.get("created_at") else None
            nodes.append({"id": f"review:{review['id']}", "review_id": review["id"], "kind": "human", "actor_kind": "human", "status": "waiting_human" if not decision else "succeeded", "review_status": review.get("status"), "decision": (decision.get("action") or decision.get("decision")) if decision else None, "reviewer_id": decision.get("actor_id") or decision.get("decided_by") if decision else None, "started_at": review.get("created_at"), "ended_at": ended_at, "duration_ms": duration_ms, "history": [dict(decision)] if decision else []})
        return {"request_id": row["r"].get("request_id"), "run_id": run_id, "config_version": row["r"].get("config_version"), "live": row["r"].get("status") in {"pending", "running"}, "nodes": nodes, "edges": edges}
    return json_value(await read_tx(tenant_id, op))


def _json_field(value):
    import json
    return json.loads(value) if value else {}
