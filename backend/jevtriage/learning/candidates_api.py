"""Learning corrections and rule-candidate APIs."""
from __future__ import annotations

import json
import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from jevtriage.auth.core import Principal, get_principal, require_roles
from jevtriage.auth.policy import can, redact_source
from jevtriage.domain.serialize import json_value
from jevtriage.ingest.service import request_meta as get_request_meta
from jevtriage.learning.apply import RuleInvariantError, validate_rule_or_raise
from jevtriage.learning.candidates import FIELDS, generate_candidates
from jevtriage.learning.candidates_store import (
    candidate_with_links,
    create_human_candidate,
    decision_marker,
    list_candidates,
    request_metas,
    supporting_corrections,
)
from jevtriage.learning.corrections import get_request_corrections, list_corrections

router = APIRouter(prefix="/api/learning", tags=["learning"])
request_router = APIRouter(prefix="/api/requests", tags=["learning"])


class HumanCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    proposed_action: dict[str, Any]
    scope: dict[str, Any]
    rationale: str = Field(min_length=1, max_length=3000)
    supporting_correction_ids: list[str] = Field(default_factory=list)


async def _readable_request(principal: Principal, request_id: str) -> bool:
    meta = await get_request_meta(principal.tenant_id, request_id)
    return bool(meta and can(principal, "learn_read", meta))


async def _readable_requests(principal: Principal, request_ids) -> dict[str, bool]:
    ids = list(set(request_ids))
    if not ids:
        return {}
    rows = await request_metas(principal.tenant_id, ids)
    return {row["id"]: bool(row["meta"] and can(principal, "learn_read", row["meta"])) for row in rows}


@router.get("/corrections")
async def corrections(field: str | None = None, request_id: str | None = None,
                      from_: str | None = Query(None, alias="from"), to: str | None = None,
                      principal: Principal = Depends(require_roles("reviewer", "rule_admin", "operator"))):  # noqa: B008
    if request_id and not await _readable_request(principal, request_id):
        raise HTTPException(404, "Request not found")
    rows = await list_corrections(principal.tenant_id, field=field, request_id=request_id,
                                  from_=from_, to=to)
    readable = await _readable_requests(principal, (row["request_id"] for row in rows))
    for row in rows:
        if not readable[row["request_id"]]:
            row.pop("ai_value", None)
            row.pop("corrected_value", None)
            row.pop("evidence_span_ids", None)
    return redact_source(principal, {"corrections": rows})


@router.get("/candidates")
async def candidates(status: str | None = None, field: str | None = None,
                     principal: Principal = Depends(require_roles("reviewer", "rule_admin", "operator"))):  # noqa: B008
    rows = await list_candidates(principal.tenant_id, status, field)
    return json_value(redact_source(principal, {"candidates": rows}))


@router.post("/candidates/generate")
async def generate(principal: Principal = Depends(get_principal)):  # noqa: B008
    if not can(principal, "learn_propose", {"tenant_id": principal.tenant_id}):
        raise HTTPException(403, "Insufficient role")
    return {"candidates": await generate_candidates(principal.tenant_id)}


@router.post("/candidates", status_code=201)
async def propose(body: HumanCandidate, principal: Principal = Depends(get_principal)):  # noqa: B008
    if not can(principal, "learn_propose", {"tenant_id": principal.tenant_id}):
        raise HTTPException(403, "Insufficient role")
    if body.field not in FIELDS:
        raise HTTPException(422, "Unsupported correction field")
    expected = {"ai_need": "ai_need", "feasibility": "feasibility",
                "urgency": "urgency", "lead_org": "lead_org"}[body.field]
    action = body.proposed_action
    if set(action) != {"set"} or not isinstance(body.scope.get("all"), list):
        raise HTTPException(422, "Invalid proposed action or scope")
    candidate_id = "cand_" + secrets.token_hex(12)
    proposed = {"schema": "rule-v1", "rule_id": f"R-{body.field.upper()}-01", "version": 1,
                "effect": "rule", "target": expected, "scope": body.scope, "action": action,
                "candidate_id": candidate_id, "decision_id": "pending"}
    try:
        validate_rule_or_raise(proposed)
    except RuleInvariantError as exc:
        raise HTTPException(422, detail={"code": "RULE_INVARIANT", "reason": str(exc)}) from exc
    except (ValueError, TypeError) as exc:
        code = "RULE_INVALID"
        raise HTTPException(422, detail={"code": code, "reason": str(exc)}) from exc
    # Scope accepts only deterministic predicates from the shared rule contract.
    for predicate in body.scope["all"]:
        if not isinstance(predicate, dict) or not (set(predicate) <= {"field", "op", "value", "signal", "catalog_task", "present", "requester_org"}):
            raise HTTPException(422, "Invalid scope predicate")
        if "field" in predicate and (predicate["field"] not in FIELDS or predicate.get("op") not in {"eq", "in"}):
            raise HTTPException(422, "Invalid classification predicate")
        if "signal" in predicate and predicate.get("op") not in {"gte", "lte"}:
            raise HTTPException(422, "Invalid signal predicate")
    valid_corrections = await supporting_corrections(
        principal.tenant_id, list(set(body.supporting_correction_ids)), body.field,
    )
    by_id = {row["id"]: row for row in valid_corrections}
    if any(cid not in by_id for cid in body.supporting_correction_ids):
        raise HTTPException(404, "Correction not found")
    readable = await _readable_requests(principal, (row["request_id"] for row in valid_corrections))
    for cid in body.supporting_correction_ids:
        if not readable[by_id[cid]["request_id"]]:
            raise HTTPException(404, "Correction not found")
    uncertainty = {"support_count": len(set(body.supporting_correction_ids)), "counter_count": 0,
                   "minimum_support": 3, "rationale": body.rationale}
    status = "제안" if len(set(body.supporting_correction_ids)) >= 3 else "자료 부족"
    await create_human_candidate(
        principal.tenant_id, candidate_id, body.field, proposed, status, principal.user_id,
        body.supporting_correction_ids, uncertainty, body.rationale,
    )
    return {"id": candidate_id, "status": status, "source": "human", "proposed_body": proposed}


@router.get("/candidates/{candidate_id}")
async def candidate_detail(candidate_id: str, principal: Principal = Depends(require_roles("reviewer", "rule_admin", "operator"))):  # noqa: B008
    row = await candidate_with_links(principal.tenant_id, candidate_id)
    if not row:
        raise HTTPException(404, "Candidate not found")
    result = dict(row["n"])
    result["proposed_body"] = json.loads(result["proposed_body"])
    result["uncertainty"] = json.loads(result["uncertainty"])
    examples = []
    readable = await _readable_requests(principal, (link["node"].get("request_id") for link in row["links"]
                                                   if link and link["node"].get("request_id")))
    for link in row["links"]:
        if not link:
            continue
        node = dict(link["node"])
        request_id = node.get("request_id")
        if request_id and not readable[request_id]:
            continue
        for key in ("ai_value", "corrected_value"):
            if node.get(key) is not None:
                try: node[key] = json.loads(node[key])
                except (TypeError, json.JSONDecodeError): pass
        for key in ("corrected_at", "created_at"):
            if node.get(key) is not None: node[key] = str(node[key])
        examples.append({"role":link["role"],"case":node})
    result["examples"] = examples
    marker = await decision_marker(principal.tenant_id, candidate_id)
    result["insufficient_approved"] = bool(marker and marker["approved"])
    result["insufficient_approval_label"] = "자료 부족 상태로 승인됨" if result["insufficient_approved"] else None
    return json_value(redact_source(principal, result))


@request_router.get("/{request_id}/corrections")
async def request_corrections(request_id: str, principal: Principal = Depends(get_principal)):  # noqa: B008
    if not principal.roles.intersection({"reviewer", "rule_admin", "operator"}) or not await _readable_request(principal, request_id):
        raise HTTPException(404, "Request not found")
    rows = await get_request_corrections(principal.tenant_id, request_id)
    if not principal.can_read_source:
        for row in rows:
            row.pop("evidence_span_ids", None)
    return redact_source(principal, {"corrections": rows})
