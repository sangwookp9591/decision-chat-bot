"""The sole normal-run creation boundary."""
from jevtriage.db.locks import lock_node_in_tx
from jevtriage.db.pinning import pin_config_for_run_in_tx
from jevtriage.domain.ids import new_id


async def start_run_in_tx(tx, tenant: str, request_id: str, revision_id: str,
                          kind: str, *, expected_active_run_id: str | None = None,
                          actor: str = "system", reason: str | None = None,
                          request_locked: bool = False) -> tuple[str, str]:
    """Lock Request, validate revision/pointer, then create Run and Job atomically."""
    if kind not in {"normal", "reanalysis"}:
        raise ValueError("unsupported active run kind")
    request = (await (await tx.run(
        "MATCH (q:Request {tenant_id:$tenant,id:$request}) RETURN q",
        tenant=tenant, request=request_id,
    )).single(strict=True))["q"] if request_locked else await lock_node_in_tx(
        tx, tenant, "Request", request_id,
    )
    if request.get("latest_revision_id") != revision_id:
        raise ValueError("stale_revision")
    if request.get("active_run_id") != expected_active_run_id:
        raise ValueError("stale_active_run")
    run_id, job_id = new_id("run"), new_id("job")
    await (await tx.run(
        "CREATE (run:Run {id:$run,tenant_id:$tenant,request_id:$request,"
        "input_revision_id:$revision,kind:$kind,status:'pending',reason:$reason,created_at:datetime()}) "
        "CREATE (job:Job {id:$job,tenant_id:$tenant,run_id:$run,kind:'judgment',"
        "input_revision_id:$revision,status:'pending',lease_generation:0,"
        "created_by:$actor,created_at:datetime()})",
        run=run_id, job=job_id, tenant=tenant, request=request_id,
        revision=revision_id, kind=kind, reason=reason, actor=actor,
    )).consume()
    await pin_config_for_run_in_tx(tx, tenant, run_id)
    await (await tx.run(
        "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
        "SET q.active_run_id=$run,q.status=CASE WHEN q.assignment_id IS NULL "
        "THEN 'judgment_pending' ELSE q.status END",
        tenant=tenant, request=request_id, run=run_id,
    )).consume()
    return run_id, job_id
