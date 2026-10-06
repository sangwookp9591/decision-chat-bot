"""Neo4j queries for human rule candidate endpoints."""

from ildongi.db.tx import read_tx, write_tx
from ildongi.learning.candidates import candidate_json


async def request_metas(tenant: str, ids: list[str]) -> list[dict]:
    async def op(tx):
        return await (await tx.run(
            "UNWIND $ids AS id OPTIONAL MATCH (r:Request {tenant_id:$tenant,id:id}) "
            "RETURN id,properties(r) AS meta", tenant=tenant, ids=ids,
        )).data()
    return await read_tx(tenant, op)


async def list_candidates(tenant: str, status: str | None, field: str | None) -> list[dict]:
    async def op(tx):
        rows = await (await tx.run(
            "MATCH (c:RuleCandidate {tenant_id:$tenant}) "
            "WHERE ($status IS NULL OR c.status=$status) AND ($field IS NULL OR c.field=$field) "
            "RETURN c ORDER BY c.created_at DESC LIMIT 500",
            tenant=tenant, status=status, field=field,
        )).data()
        return [dict(row["c"]) for row in rows]
    return await read_tx(tenant, op)


async def supporting_corrections(tenant: str, ids: list[str], field: str) -> list[dict]:
    if not ids:
        return []
    async def op(tx):
        return await (await tx.run(
            "UNWIND $ids AS id MATCH (h:ReviewDecision {tenant_id:$tenant})-[:RECORDED]->"
            "(c:Correction {tenant_id:$tenant,id:id,field:$field}) "
            "RETURN c.id AS id,c.request_id AS request_id",
            tenant=tenant, ids=ids, field=field,
        )).data()
    return await read_tx(tenant, op)


async def create_human_candidate(tenant: str, candidate_id: str, field: str,
                                 proposed: dict, status: str, author: str,
                                 support_ids: list[str], uncertainty: dict,
                                 rationale: str) -> None:
    async def op(tx):
        await (await tx.run(
            "CREATE (n:RuleCandidate {id:$id,tenant_id:$tenant,field:$field,proposed_body:$body,"
            "status:$status,source:'human',author:$author,support_count:$support,counter_count:0,"
            "uncertainty:$uncertainty,rationale:$rationale,created_at:datetime()})",
            id=candidate_id, tenant=tenant, field=field, body=candidate_json(proposed),
            status=status, author=author, support=len(set(support_ids)),
            uncertainty=candidate_json(uncertainty), rationale=rationale,
        )).consume()
        for cid in set(support_ids):
            await (await tx.run(
                "MATCH (n:RuleCandidate {tenant_id:$tenant,id:$id}) "
                "MATCH (c:Correction {tenant_id:$tenant,id:$correction}) "
                "MERGE (n)-[:SUPPORTED_BY {role:'support'}]->(c)",
                tenant=tenant, id=candidate_id, correction=cid,
            )).consume()
    await write_tx(tenant, op)


async def candidate_with_links(tenant: str, candidate_id: str):
    async def op(tx):
        return await (await tx.run(
            "MATCH (n:RuleCandidate {tenant_id:$tenant,id:$id}) "
            "OPTIONAL MATCH (n)-[r:SUPPORTED_BY]->(s) "
            "RETURN n,collect(CASE WHEN s IS NULL THEN null ELSE {node:s,role:r.role} END) AS links",
            tenant=tenant, id=candidate_id,
        )).single()
    return await read_tx(tenant, op)


async def decision_marker(tenant: str, candidate_id: str):
    async def op(tx):
        return await (await tx.run(
            "MATCH (d:RuleDecision {tenant_id:$tenant})-[:DECIDES]->"
            "(c:RuleCandidate {tenant_id:$tenant,id:$id}) "
            "RETURN d.insufficient_approved AS approved,d.reason AS reason LIMIT 1",
            tenant=tenant, id=candidate_id,
        )).single()
    return await read_tx(tenant, op)
