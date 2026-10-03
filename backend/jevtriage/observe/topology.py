"""Request business and service topology projections."""

from jevtriage.db.tx import read_tx


async def get_topology(tenant_id: str, request_id: str, kind: str):
    async def op(tx):
        row = await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant_id,id:$request_id}) "
            "OPTIONAL MATCH (q)-[:HAS_TASK]->(t:Task {tenant_id:$tenant_id}) "
            "OPTIONAL MATCH (t)-[a:ASSIGNED_TO]->(o:Org {tenant_id:$tenant_id}) "
            "OPTIONAL MATCH (t)-[pr:PRECEDES]->(p:Task {tenant_id:$tenant_id}) "
            "RETURN q,collect(DISTINCT t) AS tasks,collect(DISTINCT o) AS orgs,"
            "collect(DISTINCT p) AS predecessors,collect(DISTINCT {from:t.id,to:o.id,role:a.role,kind:'ASSIGNED_TO'}) AS assignments,"
            "collect(DISTINCT {from:t.id,to:p.id,kind:'PRECEDES'}) AS precedences",
            tenant_id=tenant_id, request_id=request_id,
        )).single()
        if not row: return None
        if kind == "business":
            nodes=[{"id":row["q"]["id"],"type":"request"}]
            nodes += [{"id":x["id"],"type":"task","title":x.get("title"),"status":x.get("status")} for x in row["tasks"] if x]
            nodes += [{"id":x["id"],"type":"org","name":x.get("name")} for x in row["orgs"] if x]
            edges=[]
            for t in row["tasks"]:
                if t: edges.append({"from":row["q"]["id"],"to":t["id"],"kind":"HAS_TASK"})
            edges += [dict(e) for e in row["assignments"] if e and e["from"] and e["to"]]
            edges += [dict(e) for e in row["precedences"] if e and e["from"] and e["to"]]
            return {"request_id":request_id,"kind":kind,"nodes":nodes,"edges":edges}
        runs=await (await tx.run("MATCH (r:Run {tenant_id:$tenant_id,request_id:$request_id})-[:HAS_STEP]->(s:RunStep) RETURN s.kind AS kind,s.name AS name,s.status AS status,s.error_class AS error_class,s.actor AS actor",tenant_id=tenant_id,request_id=request_id)).data()
        counts={}
        for step in runs:
            service=step.get("name") or step.get("kind") or "unknown"
            item=counts.setdefault(service,{"calls":0,"errors":0,"kind":step.get("kind"),"actor":step.get("actor")})
            item["calls"]+=1; item["errors"]+=int(step.get("status")=="failed" or bool(step.get("error_class")))
        return {"request_id":request_id,"kind":kind,"services":[{"name":k,**v} for k,v in counts.items()]}
    return await read_tx(tenant_id,op)
