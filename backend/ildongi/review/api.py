"""Reviewer queue, comparison view, and CSRF protected decisions."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from ildongi.auth.core import Principal, can_review, get_principal
from ildongi.auth.policy import can, redact_source
from ildongi.domain.api_types import Int64
from ildongi.domain.drafts import draft_created_by, draft_source
from ildongi.review.service import ReviewError, decide, required_reviewer_org
from ildongi.review.store import decode, get_review, judgment_urgencies, list_reviews

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


class ClassificationChanges(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ai_need: Literal["필요", "불필요", "혼합", "정보 부족"] = Field(default=None)
    feasibility: Literal["가능", "조건부 가능", "현재 불가", "정보 부족"] = Field(default=None)
    urgency: Literal["긴급", "일반", "판단 보류"] = Field(default=None)
    lead_org: str = Field(default=None)


class DraftTaskChanges(BaseModel):
    model_config = ConfigDict(extra="forbid")
    draft_task_id: str
    title: str = Field(default=None)
    method: Literal["AI", "일반 기술", "사람"] = Field(default=None)
    lead_org: str = Field(default=None)
    collab_orgs: list[str] = Field(default=None)
    deliverable: str = Field(default=None)
    predecessors: list[str] = Field(default=None)
    reason: str = Field(default=None)


class ReviewChanges(BaseModel):
    model_config = ConfigDict(extra="forbid")
    classifications: ClassificationChanges | None = None
    draft_tasks: list[DraftTaskChanges] | None = None


class DecisionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["approve", "approve_with_changes", "reject", "request_info"]
    request_id: str
    input_revision: str
    run_id: str
    draft_version: Int64 = Field(ge=1)
    review_version: Int64 = Field(ge=1)
    changes: ReviewChanges | None = None
    reason: str | None = None
    needed_info: list[str] | None = None


def _allowed(principal: Principal, review: dict, request: dict) -> bool:
    required = required_reviewer_org(
        principal.tenant_id, review.get("required_reviewer_org") or "", principal.org_ids)
    return can_review(principal, {**dict(request), "required_reviewer_org": required})


def _list_item(principal: Principal, v: dict, request: dict, urgencies: dict, now: datetime) -> dict:
    """List entry: the stored masked title always; the masked preview only for source readers or the author."""
    created = v.get("created_at")
    item = {"id":v["id"], "request_id":v["request_id"],
            "title":request.get("title") or "",
            "run_id":v["run_id"], "revision_id":v["revision_id"],
            "draft_version":v["draft_version"],
            "review_version":v["review_version"], "status":v["status"],
            "reasons":decode(v.get("reasons"), []),
            "reasons_summary":", ".join(map(str, decode(v.get("reasons"), []))),
            "urgency":v.get("urgency", urgencies.get(v["run_id"])),
            "waiting_seconds":max(0, int((now - (created.to_native() if hasattr(created, "to_native") else created.replace(tzinfo=UTC))).total_seconds())) if created else None,
            "required_reviewer_org":v.get("required_reviewer_org")}
    if request.get("preview") and (principal.can_read_source or can(principal, "request:read", request)):
        item["preview"] = request["preview"]
    return item


def _output(row: dict, can_read_source: bool) -> dict:
    data = dict(row["o"])
    for name in ("probabilities", "legend"):
        if data.get(name):
            data[name] = json.loads(data[name])
    data["evidence"] = []
    for span in row["evidence"]:
        if span is None:
            continue
        item = {"id":span["id"], "location":decode(span["location_json"], {}),
                "probability":span["probability"]}
        if can_read_source:
            item["source_text"] = span["source_text"]
        data["evidence"].append(item)
    return data


def _draft(row: dict) -> dict:
    d = dict(row["d"])
    d["created_at"] = str(d["created_at"])
    tasks = []
    for raw in row["tasks"]:
        if raw is None:
            continue
        task = dict(raw)
        task["collab_orgs"] = decode(task.get("collab_orgs"), [])
        task["predecessors"] = decode(task.get("predecessors"), [])
        tasks.append(task)
    d["tasks"] = tasks
    d["source"] = draft_source(d["draft_version"])
    d["created_by"] = draft_created_by(d, tasks)
    return d


@router.get("")
async def reviews(status: str = Query("pending"),
                  limit: Int64 = Query(100, ge=1, le=500),  # noqa: B008
                  offset: Int64 = Query(0, ge=0),  # noqa: B008
                  principal: Principal = Depends(get_principal)):  # noqa: B008
    if status not in {"pending", "approved", "rejected", "info_requested"}:
        raise HTTPException(422, "Invalid status")
    if "reviewer" not in principal.roles:
        return {"reviews": []}
    legacy = [value for value in ("AI팀", "IT팀", "현업", "검토자")
              if required_reviewer_org(principal.tenant_id, value, principal.org_ids)
              in principal.org_ids]
    rows = await list_reviews(principal.tenant_id, status,
                              reviewer_orgs=[*principal.org_ids, *legacy],
                              limit=limit, offset=offset)
    run_ids = list({row["v"]["run_id"] for row in rows})
    urgencies = await judgment_urgencies(principal.tenant_id, run_ids)
    now = datetime.now(UTC)
    return {"reviews":[_list_item(principal, v, dict(row["q"]), urgencies, now)
                       for row in rows if (v := dict(row["v"])) and
                       _allowed(principal, v, dict(row["q"]))]}


@router.get("/{review_id}")
async def review_detail(review_id: str,
                        principal: Principal = Depends(get_principal)):  # noqa: B008
    data = await get_review(principal.tenant_id, review_id)
    if data is None or not _allowed(principal, data["review"], data["request"]):
        raise HTTPException(404, "Review not found")
    v = dict(data["review"])
    v["created_at"] = str(v["created_at"])
    v["reasons"] = decode(v.get("reasons"), [])
    request = dict(data["request"])
    if principal.can_read_source and data.get("request_text") is not None:
        request["request_text"] = data["request_text"]
    for key in ("created_at", "first_received_at"):
        if request.get(key) is not None:
            request[key] = str(request[key])
    judgment = data["judgment"]
    if judgment:
        judgment = dict(judgment)
        judgment["versions"] = decode(judgment.get("versions"), {})
        judgment["risks"] = decode(judgment.get("risks"), {})
        judgment["summary"] = decode(judgment.get("summary"), {})
        judgment["questions"] = decode(judgment.pop("questions_json", None), None)
        judgment["llm"] = decode(judgment.pop("llm_json", None), None)
        judgment["rule_effects"] = decode(judgment.get("rule_effects"), [])
        judgment["created_at"] = str(judgment["created_at"])
    history = []
    for row in data["history"]:
        item = dict(row["h"])
        item["created_at"] = str(item["created_at"])
        item["needed_info"] = decode(item.get("needed_info"), [])
        item["corrections"] = []
        for node in row["corrections"]:
            if node is None:
                continue
            correction = dict(node)
            for field in ("ai_value", "corrected_value"):
                correction[field] = decode(correction.get(field), None)
            correction["corrected_at"] = str(correction["corrected_at"])
            item["corrections"].append(correction)
        history.append(item)
    final_classifications = ({key:judgment.get(key) for key in
                              ("ai_need", "feasibility", "urgency", "lead_org")}
                             if judgment else {})
    for decision in history:
        for correction in decision["corrections"]:
            if correction["field"] in final_classifications:
                final_classifications[correction["field"]] = correction["corrected_value"]
    drafts = [_draft(row) for row in data["drafts"]]
    # AI 원안(최초 버전)과 검토 기준 초안(검토 상태의 현재 버전)을 구분해 돌려준다.
    original_draft = drafts[0] if drafts else None
    current_draft = next((d for d in drafts if d["draft_version"] == v["draft_version"]),
                         drafts[-1] if drafts else None)
    return redact_source(principal, {"review":v, "request":request, "judgment":judgment,
            "outputs":[_output(row, principal.can_read_source) for row in data["outputs"]],
            "drafts":drafts, "original_draft":original_draft, "current_draft":current_draft,
            "history":history,
            "review_version":v["review_version"],
            "final_classifications":final_classifications,
            "final_draft_version":v["draft_version"], "orgs":data.get("orgs", [])})


@router.post("/{review_id}/decision")
async def review_decision(review_id: str, command: DecisionCommand,
                          idempotency_key: str = Header(..., alias="Idempotency-Key"),
                          principal: Principal = Depends(get_principal)):  # noqa: B008
    if not idempotency_key.strip():
        raise HTTPException(422, "Idempotency-Key required")
    try:
        return await decide(principal, review_id, command.model_dump(exclude_none=True),
                            idempotency_key)
    except ReviewError as exc:
        detail = {"message":str(exc)}
        if exc.field_errors:
            detail["details"] = {"field_errors": exc.field_errors}
        if exc.latest is not None:
            detail["latest"] = exc.latest
        raise HTTPException(exc.status_code, detail) from exc
