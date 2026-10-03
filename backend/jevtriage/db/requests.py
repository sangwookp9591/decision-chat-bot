"""Request, revision and active-run pointer primitives."""

from jevtriage.db.locks import lock_node_in_tx
from jevtriage.db.tx import write_tx
from jevtriage.domain.ids import new_id


class StaleRun(RuntimeError):
    pass


async def create_request(tenant_id: str, created_by: str, *, request_id: str | None = None) -> str:
    request_id = request_id or new_id("request")

    async def op(tx):
        await (await tx.run(
            "CREATE (r:Request {id: $request_id, tenant_id: $tenant_id, "
            "created_by: $created_by, created_at: datetime(), status: 'received'})",
            request_id=request_id, tenant_id=tenant_id, created_by=created_by,
        )).consume()
        return request_id

    return await write_tx(tenant_id, op)


async def add_input_revision(tenant_id: str, request_id: str, created_by: str) -> tuple[str, int]:
    revision_id = new_id("revision")

    async def op(tx):
        await lock_node_in_tx(tx, tenant_id, "Request", request_id)
        result = await tx.run(
            "MATCH (r:Request {id: $request_id, tenant_id: $tenant_id}) "
            "SET r.revision_number = coalesce(r.revision_number, 0) + 1, "
            "r.latest_revision_id = $revision_id "
            "CREATE (i:InputRevision {id: $revision_id, tenant_id: $tenant_id, "
            "request_id: $request_id, number: r.revision_number, "
            "created_by: $created_by, created_at: datetime()}) "
            "CREATE (r)-[:HAS_REVISION]->(i) RETURN i.number AS number",
            tenant_id=tenant_id, request_id=request_id, revision_id=revision_id, created_by=created_by,
        )
        return revision_id, (await result.single(strict=True))["number"]

    return await write_tx(tenant_id, op)


async def set_active_run(tenant_id: str, request_id: str, run_id: str, revision_id: str, *, expected_active_run_id: str | None = None) -> None:
    async def op(tx):
        request = await lock_node_in_tx(tx, tenant_id, "Request", request_id)
        if request.get("active_run_id") != expected_active_run_id or request.get("latest_revision_id") != revision_id:
            raise StaleRun("request pointer or input revision changed")
        result = await tx.run(
            "MATCH (run:Run {id: $run_id, tenant_id: $tenant_id, request_id: $request_id, input_revision_id: $revision_id}) "
            "WHERE coalesce(run.kind, 'normal') <> 'shadow' RETURN run.id AS id",
            tenant_id=tenant_id, request_id=request_id, run_id=run_id, revision_id=revision_id,
        )
        if await result.single() is None:
            raise StaleRun("run absent, wrong revision, or shadow")
        await (await tx.run(
            "MATCH (r:Request {id: $request_id, tenant_id: $tenant_id}) "
            "SET r.active_run_id = $run_id",
            tenant_id=tenant_id, request_id=request_id, run_id=run_id,
        )).consume()

    await write_tx(tenant_id, op)


async def assert_active_run_in_tx(tx, tenant_id: str, request_id: str, run_id: str, revision_id: str) -> None:
    request = await lock_node_in_tx(tx, tenant_id, "Request", request_id)
    if request.get("active_run_id") != run_id or request.get("latest_revision_id") != revision_id:
        raise StaleRun("run is no longer active")
