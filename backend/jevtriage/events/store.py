"""Tenant scoped event stream support queries."""

from jevtriage.db.tx import read_tx


async def request_metas(tenant_id: str, request_ids: list[str]) -> dict[str, dict]:
    if not request_ids:
        return {}

    async def op(tx):
        result = await tx.run(
            "UNWIND $request_ids AS request_id "
            "MATCH (r:Request {tenant_id:$tenant_id, id:request_id}) "
            "RETURN r.id AS id, r.tenant_id AS tenant_id, r.created_by AS created_by, "
            "r.org_ids AS org_ids, r.shared_org_ids AS shared_org_ids, "
            "r.status AS status, r.active_run_id AS active_run_id",
            tenant_id=tenant_id, request_ids=request_ids,
        )
        return {record["id"]: dict(record) for record in await result.data()}

    return await read_tx(tenant_id, op)


async def cursor_bounds(tenant_id: str, cursor: int, *, runner=read_tx):
    async def op(tx):
        result = await tx.run(
            "OPTIONAL MATCH (c:EventCounter {tenant_id:$tenant_id}) "
            "OPTIONAL MATCH (e:Event {tenant_id:$tenant_id}) "
            "WITH coalesce(c.seq,0) AS head, c.retained_from_seq AS retained_from, "
            "min(e.created_at) AS oldest "
            "OPTIONAL MATCH (at_cursor:Event {tenant_id:$tenant_id, seq:$cursor}) "
            "RETURN head, retained_from, oldest, at_cursor.created_at AS cursor_created",
            tenant_id=tenant_id, cursor=cursor,
        )
        row = await result.single()
        return row["head"], row["retained_from"], row["oldest"], row["cursor_created"]

    return await runner(tenant_id, op)


async def request_snapshot(tenant_id: str, request_id: str) -> dict:
    async def op(tx):
        result = await tx.run(
            "MATCH (r:Request {tenant_id:$tenant_id, id:$request_id}) "
            "OPTIONAL MATCH (e:Event {tenant_id:$tenant_id, request_id:$request_id}) "
            "RETURN r.status AS status, r.active_run_id AS active_run_id, "
            "coalesce(max(e.seq),0) AS latest_seq",
            tenant_id=tenant_id, request_id=request_id,
        )
        return dict(await result.single(strict=True))

    return await read_tx(tenant_id, op)
