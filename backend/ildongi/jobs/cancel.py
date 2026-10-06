"""Atomically cancel a judgment run and fence its leased worker."""

import json
from datetime import UTC, datetime

from ildongi.auth.policy import can
from ildongi.db.events import append_event_in_tx
from ildongi.db.locks import NodeNotFound, lock_node_in_tx
from ildongi.db.tx import write_tx
from ildongi.domain.ids import new_id
from ildongi.journal.writer import JournalWriter


async def cancel_run(principal, request_id: str, run_id: str) -> dict:
    tenant = principal.tenant_id

    async def op(tx):
        try:
            request = await lock_node_in_tx(tx, tenant, "Request", request_id)
        except NodeNotFound as exc:
            raise LookupError("request not found") from exc
        if not can(principal, "request:cancel", dict(request)):
            raise PermissionError("cancel requires the author or operator")
        try:
            run = await lock_node_in_tx(tx, tenant, "Run", run_id)
        except NodeNotFound as exc:
            raise LookupError("run not found") from exc
        if run.get("request_id") != request_id:
            raise LookupError("run not found")
        status = run["status"]
        if status in {"cancelled", "failed", "judgment_saved"}:
            return {"request_id": request_id, "run_id": run_id, "status": status}, None
        if run.get("first_judgment_committed_at") is not None:
            # The final result committed first. Finish the bookkeeping under
            # these locks so a late stop cannot turn a saved result into a cancel.
            job_row = await (await tx.run(
                "MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id",
                tenant=tenant, run=run_id,
            )).single()
            if job_row:
                await lock_node_in_tx(tx, tenant, "Job", job_row["id"])
                await (await tx.run(
                    "MATCH (j:Job {tenant_id:$tenant,id:$job}) SET j.status='completed'",
                    tenant=tenant, job=job_row["id"],
                )).consume()
            await (await tx.run(
                "MATCH (r:Run {tenant_id:$tenant,id:$run}) "
                "SET r.status='judgment_saved',r.ended_at=coalesce(r.ended_at,datetime())",
                tenant=tenant, run=run_id,
            )).consume()
            return {"request_id": request_id, "run_id": run_id, "status": "judgment_saved"}, None
        if request.get("active_run_id") != run_id:
            raise ValueError("run is no longer active")
        job_row = await (await tx.run(
            "MATCH (j:Job {tenant_id:$tenant,run_id:$run}) RETURN j.id AS id",
            tenant=tenant, run=run_id,
        )).single()
        if job_row is None:
            raise LookupError("job not found")
        job = await lock_node_in_tx(tx, tenant, "Job", job_row["id"])
        # The Run lock serializes completion against cancellation; the Job lock
        # also serializes claim and fences all existing worker generations.
        step_row = await (await tx.run(
            "MATCH (s:RunStep {tenant_id:$tenant,run_id:$run,status:'running'}) "
            "RETURN s.name AS name ORDER BY s.started_at DESC LIMIT 1",
            tenant=tenant, run=run_id,
        )).single()
        stage = step_row["name"] if step_row else ("대기 중" if status == "pending" else "실행 중")
        await (await tx.run(
            "MATCH (s:RunStep {tenant_id:$tenant,run_id:$run,status:'running'}) "
            "WITH s,datetime() AS ended "
            "SET s.status='cancelled',s.error_class='CancelledByUser',s.ended_at=ended, "
            "s.duration_ms=ended.epochMillis-s.started_at.epochMillis",
            tenant=tenant, run=run_id,
        )).consume()
        attempts = json.loads(run.get("attempts_json") or "[]")
        for attempt in attempts:
            if attempt.get("status") == "running":
                attempt.update(status="cancelled", error_class="CancelledByUser")
        await (await tx.run(
            "MATCH (r:Run {tenant_id:$tenant,id:$run}) "
            "MATCH (j:Job {tenant_id:$tenant,id:$job}) "
            "SET r.status='cancelled',r.cancelled_by=$actor,r.cancelled_at=datetime(), "
            "r.cancelled_step=$stage,r.ended_at=datetime(),r.attempts_json=$attempts, "
            "j.status='cancelled',j.lease_generation=coalesce(j.lease_generation,0)+1, "
            "j.lease_expires_at=null "
            "RETURN r.id",
            tenant=tenant, run=run_id, job=job["id"], actor=principal.user_id,
            stage=stage, attempts=json.dumps(attempts),
        )).single(strict=True)
        await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant,id:$request,active_run_id:$run}) "
            "SET q.status='cancelled'",
            tenant=tenant, request=request_id, run=run_id,
        )).consume()
        await append_event_in_tx(tx, tenant, "judgment.cancelled",
                                 {"request_id": request_id, "run_id": run_id,
                                  "status": "cancelled", "cancelled_by": principal.user_id,
                                  "stage": stage}, request_id=request_id, run_id=run_id)
        return {"request_id": request_id, "run_id": run_id, "status": "cancelled"}, stage

    result, stage = await write_tx(tenant, op)
    if stage is not None:
        JournalWriter().append({
            "event_id": new_id("event"), "attempt_id": new_id("attempt"),
            "request_id": request_id, "run_id": run_id, "kind": "worker_run",
            "ts": datetime.now(UTC).isoformat(), "status_code": "cancelled",
            "tenant_id": tenant, "step_name": stage,
        })
    return result
