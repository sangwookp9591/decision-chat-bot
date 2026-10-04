"""Durable progress projection query for judgment runs."""

import json

from jevtriage.db.tx import read_tx
from jevtriage.domain.serialize import to_native


def _elapsed(start, end):
    if start is None or end is None:
        return None
    return max(0, round((end.to_native() - start.to_native()).total_seconds() * 1000))


async def get_progress(tenant_id: str, request_id: str, run_id: str | None = None) -> dict | None:
    async def op(tx):
        row = await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
            "MATCH (r:Run {tenant_id:$tenant,request_id:$request}) "
            "WHERE r.id=coalesce($run,q.active_run_id) "
            "OPTIONAL MATCH (r)-[:HAS_STEP]->(s:RunStep {tenant_id:$tenant}) "
            "RETURN q.status AS request_status,q.first_received_at AS received, "
            "r AS run,collect(s) AS steps",
            tenant=tenant_id, request=request_id, run=run_id,
        )).single()
        if row is None:
            return None
        run = dict(row["run"])
        steps = [{"name": step["name"], "kind": step["kind"],
                  "status": step["status"],
                  "started_at": to_native(step.get("started_at")),
                  "ended_at": to_native(step.get("ended_at"))}
                 for step in row["steps"] if step]
        steps.sort(key=lambda step: (step["started_at"] or "", step["name"]))
        preliminary = json.loads(run["preliminary_json"]) if run.get("preliminary_json") else None
        final = run.get("first_judgment_committed_at") is not None
        status = run.get("status") or row["request_status"]
        if status in {"pending", "running"}:
            status = "processing"
        return {"request_id": request_id, "run_id": run["id"],
                "status": status,
                "steps": steps, "preliminary": preliminary,
                "evidence_ready": run.get("evidence_ready_at") is not None,
                "tasks_ready": run.get("tasks_ready_at") is not None,
                "final": final,
                "timings_ms": {
                    "received_to_preliminary": _elapsed(row["received"], run.get("preliminary_at")),
                    "received_to_final": _elapsed(row["received"], run.get("first_judgment_committed_at")),
                }}
    return await read_tx(tenant_id, op)
