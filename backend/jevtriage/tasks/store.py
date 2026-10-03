"""Tenant scoped task and draft queries."""
from __future__ import annotations

import json

from jevtriage.db.tx import read_tx


async def lock_task_in_tx(tx, tenant_id: str, task_id: str):
    """Serialize a Task transition within its tenant."""
    row = await (await tx.run(
        "MATCH (t:Task {tenant_id:$tenant,id:$id}) "
        "SET t._lock=randomUUID() RETURN t",
        tenant=tenant_id, id=task_id,
    )).single()
    return row["t"] if row else None


async def list_tasks(tenant_id: str, filters: dict) -> list[dict]:
    async def op(tx):
        rows = await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant})-[:HAS_TASK]->(t:Task {tenant_id:$tenant}) "
            "OPTIONAL MATCH (t)-[a:ASSIGNED_TO]->(o:Org {tenant_id:$tenant}) "
            "OPTIONAL MATCH (p:Task {tenant_id:$tenant})-[:PRECEDES]->(t) "
            "RETURN q,t,collect(DISTINCT {org:o.id,role:a.role}) AS orgs,"
            "collect(DISTINCT p) AS predecessors ORDER BY t.created_at DESC",
            tenant=tenant_id,
        )).data()
        result=[]
        for row in rows:
            t=dict(row['t']); q=dict(row['q'])
            t['collab_orgs']=json.loads(t.get('collab_orgs') or '[]')
            t['predecessors']=json.loads(t.get('predecessors') or '[]')
            t['orgs']=[x for x in row['orgs'] if x.get('org')]
            t['predecessor_tasks']=[dict(x) for x in row['predecessors'] if x]
            t['request_status']=q.get('status'); t['request_title']=q.get('title')
            t['created_by']=q.get('created_by'); t['org_ids']=q.get('shared_org_ids') or q.get('org_ids') or []
            result.append(t)
        return result
    return await read_tx(tenant_id, op)


async def get_task(tenant_id: str, task_id: str) -> dict | None:
    async def op(tx):
        row=await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant})-[:HAS_TASK]->(t:Task {tenant_id:$tenant,id:$id}) "
            "OPTIONAL MATCH (t)-[a:ASSIGNED_TO]->(o:Org {tenant_id:$tenant}) "
            "OPTIONAL MATCH (p:Task {tenant_id:$tenant})-[:PRECEDES]->(t) "
            "OPTIONAL MATCH (t)-[:PRECEDES]->(n:Task {tenant_id:$tenant}) "
            "RETURN q,t,collect(DISTINCT {org:o.id,role:a.role}) AS orgs,"
            "collect(DISTINCT p) AS predecessors,collect(DISTINCT n) AS successors",
            tenant=tenant_id,id=task_id,
        )).single()
        if not row:return None
        t=dict(row['t']); q=dict(row['q'])
        for key in ('collab_orgs','predecessors'): t[key]=json.loads(t.get(key) or '[]')
        t['orgs']=[x for x in row['orgs'] if x.get('org')]
        t['predecessor_tasks']=[dict(x) for x in row['predecessors'] if x]
        t['successors']=[dict(x) for x in row['successors'] if x]
        t['request']={k:q.get(k) for k in ('id','title','status','created_by','org_ids','shared_org_ids')}
        t['request']['org_ids']=t['request'].get('shared_org_ids') or t['request'].get('org_ids') or []
        return t
    return await read_tx(tenant_id,op)
