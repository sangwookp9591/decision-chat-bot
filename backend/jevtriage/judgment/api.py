"""Read-only judgment and run history API."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query

from jevtriage.auth.core import Principal, can_view_request, get_principal
from jevtriage.domain.serialize import json_value
from jevtriage.ingest.store import get_request_meta
from jevtriage.judgment.store import get_judgment, list_runs

router = APIRouter(prefix="/api")


def _date(value):
    return json_value(value)


async def _visible_request(principal: Principal, request_id: str) -> dict:
    meta = await get_request_meta(principal.tenant_id, request_id)
    if meta is None or not can_view_request(principal, meta):
        raise HTTPException(status_code=404, detail="Request not found")
    return meta


@router.get("/requests/{request_id}/judgment")
async def judgment(request_id: str, run_id: str | None = Query(None),
                   principal: Principal = Depends(get_principal)):  # noqa: B008
    meta = await _visible_request(principal, request_id)
    chosen_run = run_id or meta.get("active_run_id")
    if not chosen_run:
        raise HTTPException(status_code=404, detail="Judgment not found")
    data = await get_judgment(principal.tenant_id, request_id, chosen_run)
    if data is None:
        raise HTTPException(status_code=404, detail="Judgment not found")
    j = data["judgment"]
    outputs = []
    for row in data["outputs"]:
        o = dict(row["o"])
        item = {"id": o["id"], "question_id": o["question_id"], "type": o["type"],
                "value": o["value"], "model": o["model"]}
        if o.get("confidence") is not None:
            item["confidence"] = o["confidence"]
        if o.get("probabilities") is not None:
            item["probabilities"] = json.loads(o["probabilities"])
        if o.get("noul") is not None:
            item["noul"] = o["noul"]
        if o.get("legend") is not None:
            item["legend"] = json.loads(o["legend"])
        item["evidence"] = []
        for citation in row["citations"]:
            if citation is None:
                continue
            evidence = {"id": citation["id"], "source": citation["source"] or
                        ("attachment" if citation["attachment_id"] else "chat"),
                        "attachment_id": citation["attachment_id"],
                        "location": json.loads(citation["location_json"]),
                        "char_start": citation["char_start"], "char_end": citation["char_end"],
                        "probability": citation["prob"]}
            if principal.can_read_source:
                evidence["source_text"] = citation["source_text"]
            item["evidence"].append(evidence)
        outputs.append(item)
    tasks = []
    for row in data["drafts"]:
        task = dict(row["t"])
        tasks.append({key: task.get(key) for key in ("id", "draft_task_id", "draft_version",
                      "title", "method", "lead_org", "deliverable", "status", "reason", "author")}
                     | {"collab_orgs": json.loads(task.get("collab_orgs") or "[]"),
                        "predecessors": json.loads(task.get("predecessors") or "[]")})
    review = data["review"]
    return {"id": j["id"], "request_id": request_id, "revision_id": j["revision_id"],
            "run_id": chosen_run, "classifications": {key: j.get(key) for key in
                ("ai_need", "feasibility", "urgency", "lead_org")},
            "risk_confirmed": j["risk_confirmed"], "risks": json.loads(j["risks"]),
            "summary": json.loads(j["summary"]), "author": j["author"],
            "versions": json.loads(j["versions"]), "mode": j["mode"],
            "rule_effects": json.loads(j.get("rule_effects") or "[]"),
            "created_at": _date(j["created_at"]), "outputs": outputs, "draft_tasks": tasks,
            "review_reasons": json.loads(review["reasons"]) if review else [],
            "review": {"id": review["id"], "status": review["status"],
                       "required_reviewer_org": review["required_reviewer_org"]} if review else None}


@router.get("/requests/{request_id}/runs")
async def runs(request_id: str, principal: Principal = Depends(get_principal)):  # noqa: B008
    meta = await _visible_request(principal, request_id)
    rows = await list_runs(principal.tenant_id, request_id)
    return {"active_run_id": meta.get("active_run_id"), "runs": [
        {"id": r["r"]["id"], "revision_id": r["r"].get("input_revision_id"),
         "status": r["r"].get("status"), "versions": json.loads(r["r"].get("versions_json") or "{}"),
         "created_at": _date(r["r"].get("created_at")),
         "first_judgment_committed_at": _date(r["r"].get("first_judgment_committed_at"))}
        for r in rows]}
