"""Tenant scoped review snapshots and immutable decision history."""
from __future__ import annotations

import json

from jevtriage.db.tx import read_tx


def decode(value, default):
    return json.loads(value) if value else default


async def get_review(tenant_id: str, review_id: str) -> dict | None:
    async def op(tx):
        row = await (await tx.run(
            "MATCH (v:Review {tenant_id:$tenant,id:$id}) "
            "MATCH (q:Request {tenant_id:$tenant,id:v.request_id}) "
            "RETURN v,q", tenant=tenant_id, id=review_id,
        )).single()
        if row is None:
            return None
        review, request = dict(row["v"]), dict(row["q"])
        result = await (await tx.run(
            "MATCH (j:Judgment {tenant_id:$tenant,run_id:$run}) "
            "RETURN j ORDER BY j.created_at DESC LIMIT 1",
            tenant=tenant_id, run=review["run_id"],
        )).single()
        judgment = dict(result["j"]) if result else None
        outputs = await (await tx.run(
            "MATCH (o:ModelOutput {tenant_id:$tenant,run_id:$run}) "
            "OPTIONAL MATCH (o)-[c:CITES]->(e:EvidenceSpan {tenant_id:$tenant}) "
            "RETURN o,collect(CASE WHEN e IS NULL THEN null ELSE "
            "{id:e.id,location_json:e.location_json,probability:c.prob,source_text:e.source_text} END) AS evidence",
            tenant=tenant_id, run=review["run_id"],
        )).data()
        drafts = await (await tx.run(
            "MATCH (d:Draft {tenant_id:$tenant,run_id:$run}) "
            "OPTIONAL MATCH (t:DraftTask {tenant_id:$tenant})-[:IN_DRAFT]->(d) "
            "RETURN d,collect(t) AS tasks ORDER BY d.draft_version",
            tenant=tenant_id, run=review["run_id"],
        )).data()
        history = await (await tx.run(
            "MATCH (v:Review {tenant_id:$tenant,id:$id})-[:HAS_DECISION]->(h:ReviewDecision) "
            "OPTIONAL MATCH (h)-[:RECORDED]->(c:Correction {tenant_id:$tenant}) "
            "RETURN h,collect(c) AS corrections ORDER BY h.created_at",
            tenant=tenant_id, id=review_id,
        )).data()
        return {"review": review, "request": request, "judgment": judgment,
                "outputs": outputs, "drafts": drafts, "history": history}
    return await read_tx(tenant_id, op)


async def list_reviews(tenant_id: str, status: str, limit: int = 100) -> list[dict]:
    async def op(tx):
        return await (await tx.run(
            "MATCH (v:Review {tenant_id:$tenant,status:$status}) "
            "MATCH (q:Request {tenant_id:$tenant,id:v.request_id}) "
            "WHERE q.active_run_id=v.run_id AND q.latest_revision_id=v.revision_id "
            "RETURN v,q ORDER BY v.created_at DESC LIMIT $limit",
            tenant=tenant_id, status=status, limit=limit,
        )).data()
    return await read_tx(tenant_id, op)
