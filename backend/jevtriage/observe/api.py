"""Authenticated, read-only execution observation endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException

from jevtriage.auth.core import Principal, can_view_request, get_principal
from jevtriage.db.tx import read_tx
from jevtriage.domain.serialize import json_value
from jevtriage.observe.flow import get_flow
from jevtriage.observe.playback import get_playback
from jevtriage.observe.topology import get_topology

router = APIRouter(prefix="/api/observe", tags=["observe"])


async def _request_meta(principal: Principal, request_id: str):
    async def op(tx):
        row = await (await tx.run("MATCH (r:Request {tenant_id:$tenant_id,id:$request_id}) RETURN r",tenant_id=principal.tenant_id,request_id=request_id)).single()
        return dict(row["r"]) if row else None
    meta=await read_tx(principal.tenant_id,op)
    if not meta or not can_view_request(principal,meta): raise HTTPException(404,"Request not found")
    return meta


async def _run_meta(principal: Principal, run_id: str):
    async def op(tx):
        row=await (await tx.run("MATCH (r:Run {tenant_id:$tenant_id,id:$run_id}) RETURN r.request_id AS request_id",tenant_id=principal.tenant_id,run_id=run_id)).single()
        return row["request_id"] if row else None
    request_id=await read_tx(principal.tenant_id,op)
    if not request_id: raise HTTPException(404,"Run not found")
    await _request_meta(principal,request_id)
    return request_id


@router.get("/runs/{run_id}/flow")
async def flow(run_id: str, principal: Principal = Depends(get_principal)):  # noqa: B008
    request_id=await _run_meta(principal,run_id)
    result=await get_flow(principal.tenant_id,run_id)
    result["request_id"]=request_id
    return result


@router.get("/runs/{run_id}/playback")
async def playback(run_id: str, principal: Principal = Depends(get_principal)):  # noqa: B008
    request_id=await _run_meta(principal,run_id)
    result=await get_playback(principal.tenant_id,run_id)
    result["request_id"]=request_id
    return result


@router.get("/requests/{request_id}/topology")
async def topology(request_id: str, kind: str = "business", principal: Principal = Depends(get_principal)):  # noqa: B008
    if kind not in {"business","service"}: raise HTTPException(422,"kind must be business or service")
    await _request_meta(principal,request_id)
    return await get_topology(principal.tenant_id,request_id,kind)


@router.get("/steps/{step_id}")
async def step_detail(step_id: str, principal: Principal = Depends(get_principal)):  # noqa: B008
    async def op(tx):
        row=await (await tx.run(
            "MATCH (s:RunStep {tenant_id:$tenant_id,id:$step_id}) "
            "MATCH (r:Run {tenant_id:$tenant_id,id:s.run_id}) RETURN s,r.request_id AS request_id,r.config_version AS config_version",
            tenant_id=principal.tenant_id,step_id=step_id)).single()
        return dict(row["s"])|{"request_id":row["request_id"],"config_version":row["config_version"]} if row else None
    item=await read_tx(principal.tenant_id,op)
    if not item: raise HTTPException(404,"Step not found")
    await _request_meta(principal,item["request_id"])
    item["versions"]=_loads(item.pop("versions_json",None))
    item["input_summary"]=_loads(item.pop("input_summary_json",None))
    item["output_summary"]=_loads(item.pop("output_summary_json",None))
    item["actor_kind"]=item.get("actor") if item.get("actor") in {"ai","code","rule","external","human"} else item.get("kind")
    async def details(tx):
        judgment = await (await tx.run(
            "MATCH (j:Judgment {tenant_id:$tenant_id,run_id:$run_id}) "
            "OPTIONAL MATCH (o:ModelOutput {tenant_id:$tenant_id,run_id:$run_id})-[:OF_JUDGMENT]->(j) "
            "OPTIONAL MATCH (o)-[c:CITES]->(e:EvidenceSpan {tenant_id:$tenant_id}) "
            "RETURN j,collect(DISTINCT {question_id:o.question_id,value:o.value,confidence:o.confidence,probabilities:o.probabilities,noul:o.noul,evidence:CASE WHEN e IS NULL THEN null ELSE {id:e.id,location_json:e.location_json,probability:c.prob} END}) AS outputs",
            tenant_id=principal.tenant_id,run_id=item["run_id"])).single()
        reviews=await (await tx.run(
            "MATCH (v:Review {tenant_id:$tenant_id,run_id:$run_id}) "
            "OPTIONAL MATCH (v)-[:HAS_DECISION]->(h:ReviewDecision) "
            "OPTIONAL MATCH (h)-[:RECORDED]->(c:Correction) "
            "RETURN v,collect(DISTINCT h) AS history,collect(DISTINCT c) AS corrections ORDER BY v.created_at",
            tenant_id=principal.tenant_id,run_id=item["run_id"])).data()
        return judgment, reviews
    judgment,reviews=await read_tx(principal.tenant_id,details)
    item["judgment"] = ({"id":judgment["j"]["id"],"ai_need":judgment["j"].get("ai_need"),"feasibility":judgment["j"].get("feasibility"),"urgency":judgment["j"].get("urgency"),"lead_org":judgment["j"].get("lead_org"),"risk_confirmed":judgment["j"].get("risk_confirmed"),"versions":_loads(judgment["j"].get("versions")),"outputs":judgment["outputs"]} if judgment else None)
    item["review_history"] = [{"review_id":r["v"]["id"],"created_at":r["v"].get("created_at"),"status":r["v"].get("status"),"history":r["history"],"corrections":r["corrections"]} for r in reviews]
    if item.get("kind") == "rule":
        async def applications(tx):
            return await (await tx.run(
                "MATCH (s:RunStep {tenant_id:$tenant_id,id:$step_id})-[a:APPLIED]->(v:RuleVersion {tenant_id:$tenant_id}) "
                "RETURN v.rule_id AS rule_id,v.version AS version,v.body AS body,a.outcome AS outcome,"
                "a.before AS before,a.after AS after,s.config_version AS step_config_version",
                tenant_id=principal.tenant_id, step_id=step_id)).data()
        rows = await read_tx(principal.tenant_id, applications)
        item["rule_applications"] = [{
            "rule_version": f"{r['rule_id']}@{r['version']}",
            "rule_id": r["rule_id"], "version": r["version"],
            "effect": _loads(r.get("body")).get("effect"), "outcome": r["outcome"],
            "before": _loads(r.get("before")), "after": _loads(r.get("after")),
            "config_versions": [v for v in (r.get("step_config_version"), item.get("config_version")) if v is not None],
        } for r in rows]
    item["source_links"] = ([{"id":output["evidence"]["id"], "url":f"/api/requests/{item['request_id']}/evidence/{output['evidence']['id']}", "location":_loads(output["evidence"].get("location_json"))} for output in (item["judgment"] or {}).get("outputs", []) if output and output.get("evidence")] if principal.can_read_source else [])
    if item["judgment"]:
        for output in item["judgment"]["outputs"]:
            if output and output.get("evidence"):
                output["evidence"].pop("location_json",None)
                if not principal.can_read_source:
                    output["evidence"] = None
    return json_value(item)


def _loads(value):
    return json.loads(value) if value else {}
