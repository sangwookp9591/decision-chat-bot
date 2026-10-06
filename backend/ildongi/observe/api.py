"""Authenticated, read-only execution observation endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from ildongi.auth.core import Principal, get_principal
from ildongi.auth.policy import can, redact_source
from ildongi.domain.serialize import json_value, loads_or
from ildongi.ingest.service import request_meta as get_request_meta
from ildongi.observe.flow import get_flow
from ildongi.observe.playback import get_playback
from ildongi.observe.topology import get_topology
from ildongi.observe.trace_store import (
    run_request_id,
    step_details,
    step_rule_applications,
    step_with_run,
)

router = APIRouter(prefix="/api/observe", tags=["observe"])


async def _request_meta(principal: Principal, request_id: str):
    meta = await get_request_meta(principal.tenant_id, request_id)
    if not meta or not can(principal,"view_trace",meta): raise HTTPException(404,"Request not found")
    return meta


async def _run_meta(principal: Principal, run_id: str):
    request_id=await run_request_id(principal.tenant_id,run_id)
    if not request_id: raise HTTPException(404,"Run not found")
    await _request_meta(principal,request_id)
    return request_id


@router.get("/runs/{run_id}/flow")
async def flow(run_id: str, principal: Principal = Depends(get_principal)):  # noqa: B008
    request_id=await _run_meta(principal,run_id)
    result=await get_flow(principal.tenant_id,run_id)
    result["request_id"]=request_id
    return redact_source(principal, result)


@router.get("/runs/{run_id}/playback")
async def playback(run_id: str, principal: Principal = Depends(get_principal)):  # noqa: B008
    request_id=await _run_meta(principal,run_id)
    result=await get_playback(principal.tenant_id,run_id)
    result["request_id"]=request_id
    return redact_source(principal, result)


@router.get("/requests/{request_id}/topology")
async def topology(request_id: str, kind: str = "business", principal: Principal = Depends(get_principal)):  # noqa: B008
    if kind not in {"business","service"}: raise HTTPException(422,"kind must be business or service")
    await _request_meta(principal,request_id)
    return redact_source(principal, await get_topology(principal.tenant_id,request_id,kind))


@router.get("/steps/{step_id}")
async def step_detail(step_id: str, principal: Principal = Depends(get_principal)):  # noqa: B008
    item=await step_with_run(principal.tenant_id,step_id)
    if not item: raise HTTPException(404,"Step not found")
    await _request_meta(principal,item["request_id"])
    item["versions"]=_loads(item.pop("versions_json",None))
    item["input_summary"]=_loads(item.pop("input_summary_json",None))
    item["output_summary"]=_loads(item.pop("output_summary_json",None))
    item["actor_kind"]=item.get("actor") if item.get("actor") in {"ai","code","rule","external","human"} else item.get("kind")
    judgment,reviews=await step_details(principal.tenant_id,item["run_id"])
    item["judgment"] = ({"id":judgment["j"]["id"],"ai_need":judgment["j"].get("ai_need"),"feasibility":judgment["j"].get("feasibility"),"urgency":judgment["j"].get("urgency"),"lead_org":judgment["j"].get("lead_org"),"risk_confirmed":judgment["j"].get("risk_confirmed"),"versions":_loads(judgment["j"].get("versions")),"outputs":judgment["outputs"]} if judgment else None)
    item["review_history"] = [{"review_id":r["v"]["id"],"created_at":r["v"].get("created_at"),"status":r["v"].get("status"),"history":r["history"],"corrections":r["corrections"]} for r in reviews]
    if item.get("kind") == "rule":
        rows = await step_rule_applications(principal.tenant_id, step_id)
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
    return json_value(redact_source(principal, item))


def _loads(value):
    return loads_or(value, {})
