"""Tenant-scoped durable Run and RunStep trace storage.

Writes are transaction helpers: callers must establish worker ownership first.
"""

import json

from jevtriage.db.tx import read_tx
from jevtriage.domain.ids import new_id


def _json(value):
    return json.dumps(value or {}, ensure_ascii=False, separators=(",", ":"))


async def start_step_in_tx(tx, *, tenant_id, run_id, name, kind, actor, versions,
                           attempt_id, parent_step_id=None, predecessor_ids=(), input_summary=None):
    step_id = new_id("step")
    result = await tx.run(
        "MATCH (r:Run {tenant_id: $tenant_id, id: $run_id}) "
        "CREATE (s:RunStep {id: $step_id, tenant_id: $tenant_id, run_id: $run_id, "
        "name: $name, kind: $kind, status: 'running', started_at: datetime(), "
        "actor: $actor, versions_json: $versions, attempt_id: $attempt_id, "
        "parent_step_id: $parent_step_id, predecessor_ids: $predecessor_ids, "
        "input_summary_json: $input_summary}) CREATE (r)-[:HAS_STEP]->(s) "
        "RETURN s.id AS id",
        tenant_id=tenant_id, run_id=run_id, step_id=step_id, name=name, kind=kind,
        actor=actor, versions=_json(versions), attempt_id=attempt_id,
        parent_step_id=parent_step_id, predecessor_ids=list(predecessor_ids),
        input_summary=_json(input_summary),
    )
    if await result.single() is None:
        raise LookupError("run absent")
    return step_id


async def finish_step_in_tx(tx, *, tenant_id, step_id, status, error_class=None,
                            output_summary=None):
    if status not in {"succeeded", "failed", "skipped", "waiting_human"}:
        raise ValueError("invalid step terminal status")
    result = await tx.run(
        "MATCH (s:RunStep {tenant_id: $tenant_id, id: $step_id, status: 'running'}) "
        "WITH s, datetime() AS ended "
        "SET s.status = $status, s.ended_at = ended, "
        "s.duration_ms = ended.epochMillis - s.started_at.epochMillis, "
        "s.error_class = $error_class, s.output_summary_json = $output_summary "
        "RETURN s.duration_ms AS duration_ms",
        tenant_id=tenant_id, step_id=step_id, status=status,
        error_class=error_class, output_summary=_json(output_summary),
    )
    record = await result.single()
    if record is None:
        raise ValueError("step absent or already terminal")
    return record["duration_ms"]


async def get_trace(tenant_id: str, run_id: str):
    """Return the saved run, attempts and steps; no raw inputs are stored here."""
    async def op(tx):
        result = await tx.run(
            "MATCH (r:Run {tenant_id: $tenant_id, id: $run_id}) "
            "OPTIONAL MATCH (r)-[:HAS_STEP]->(s:RunStep {tenant_id: $tenant_id}) "
            "RETURN r, collect(s) AS steps",
            tenant_id=tenant_id, run_id=run_id,
        )
        row = await result.single()
        if row is None:
            return None
        run = dict(row["r"])
        run["versions"] = json.loads(run.pop("versions_json", "{}"))
        run["attempts"] = json.loads(run.pop("attempts_json", "[]"))
        steps = []
        for node in row["steps"]:
            item = dict(node)
            for field in ("versions", "input_summary", "output_summary"):
                item[field] = json.loads(item.pop(f"{field}_json", "{}"))
            steps.append(item)
        steps.sort(key=lambda item: (str(item.get("started_at", "")), item["id"]))
        return {"run": run, "steps": steps}

    return await read_tx(tenant_id, op)
