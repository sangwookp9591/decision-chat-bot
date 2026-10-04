from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from jevtriage.auth.core import Principal, get_principal
from jevtriage.auth.policy import can
from jevtriage.db.tx import read_tx, write_tx

ROOT = Path(__file__).resolve().parents[3]
router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])
LABEL_FIELDS = {"ai_need", "feasibility", "urgency", "team_set", "risk_areas"}


def consensus_state(labels: list[dict[str, Any]]) -> str:
    if not labels:
        return "unlabeled"
    if len(labels) == 1:
        return "single_label"
    signatures = [json.dumps(x, sort_keys=True, ensure_ascii=False) for x in labels]
    return "agreed" if len(set(signatures)) == 1 else "consensus_required"


def progress_summary(total: int, labels: list[dict[str, Any]]) -> dict[str, int]:
    latest: dict[str, str] = {}
    for item in labels:
        latest[item["id"]] = item["status"]
    confirmed = sum(status == "confirmed" for status in latest.values())
    deferred = sum(status == "deferred" for status in latest.values())
    return {"total": total, "confirmed": confirmed, "deferred": deferred,
            "remaining": max(0, total - confirmed - deferred),
            "percent": round(confirmed * 100 / total) if total else 100}


def visible_candidate(row: dict[str, Any], split: str) -> dict[str, Any]:
    result = dict(row)
    if split == "final":
        for key in ("prediction", "predictions", "model_output", "model_result", "model_results",
                    "proposed_labels", "rationale", "scenario_tags"):
            result.pop(key, None)
    return result


def _rows(split: str) -> list[dict[str, Any]]:
    if split not in {"tuning", "final"}:
        raise HTTPException(422, "Unknown split")
    path = ROOT / "eval/candidates" / f"{split}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


async def _allowed(principal: Principal) -> bool:
    return can(principal, "eval_label", {"tenant_id": principal.tenant_id})


async def _labels(tenant: str, split: str) -> list[dict[str, Any]]:
    async def op(tx):
        result = await tx.run(
            "MATCH (l:EvalLabel {tenant_id:$tenant,split:$split}) "
            "RETURN l.sample_id AS id,l.labels AS labels,l.status AS status,l.user_id AS user_id,"
            "l.reason AS reason,l.confidence AS confidence,l.created_at AS created_at "
            "ORDER BY l.created_at", tenant=tenant, split=split)
        return await result.data()
    return await read_tx(tenant, op)


def _latest_by_user(labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for item in labels:
        latest[(item["id"], item["user_id"])] = {**item, "labels": json.loads(item["labels"])}
    return list(latest.values())


@router.get("/candidates")
async def candidates(split: str = "tuning", principal: Principal = Depends(get_principal)):  # noqa: B008
    if not await _allowed(principal):
        raise HTTPException(403, "Insufficient role")
    rows = _rows(split)
    all_labels = _latest_by_user(await _labels(principal.tenant_id, split))
    by_id: dict[str, list[dict[str, Any]]] = {}
    for item in all_labels:
        by_id.setdefault(item["id"], []).append(item)
    enriched = []
    for row in rows:
        decisions = by_id.get(row["id"], [])
        resolution = next((item for item in reversed(decisions) if item["status"] == "consensus_confirmed"), None)
        votes = [item for item in decisions if item["status"] == "confirmed"]
        resolved = resolution and all(str(resolution["created_at"]) >= str(item["created_at"]) for item in votes)
        state = "resolved" if resolved else consensus_state([item["labels"] for item in votes])
        own_decision = next((item for item in decisions if item["user_id"] == principal.user_id), None)
        enriched.append(visible_candidate({**row, "labels": decisions, "my_labels": own_decision,
                                           "consensus": state}, split))
    return {"split": split, "candidates": enriched,
            "progress": progress_summary(len(rows), [item for item in all_labels if item["user_id"] == principal.user_id])}


class LabelBody(BaseModel):
    labels: dict[str, Any] = Field(...)
    status: str = "confirmed"
    reason: str | None = None
    confidence: float = Field(ge=0, le=1)


async def _record(principal: Principal, split: str, sample_id: str, body: LabelBody, action: str) -> None:
    async def store(tx):
        await (await tx.run(
            "CREATE (l:EvalLabel {tenant_id:$tenant,split:$split,sample_id:$id,user_id:$user,"
            "labels:$labels,status:$status,reason:$reason,confidence:$confidence,created_at:datetime()}) "
            "CREATE (a:AuditEvent {tenant_id:$tenant,kind:'evaluation_label',actor:$user,"
            "subject:$id,action:$action,reason:$reason,created_at:datetime()})",
            tenant=principal.tenant_id, split=split, id=sample_id, user=principal.user_id,
            labels=json.dumps(body.labels, ensure_ascii=False), status=("consensus_confirmed" if action == "evaluation_consensus_confirmed" else body.status),
            reason=body.reason, confidence=body.confidence, action=action)).consume()
    await write_tx(principal.tenant_id, store)


def _validate_labels(split: str, sample_id: str, body: LabelBody) -> None:
    if not any(x["id"] == sample_id for x in _rows(split)):
        raise HTTPException(404, "Sample not found")
    if body.status not in {"confirmed", "deferred"} or (body.status == "deferred" and not body.reason):
        raise HTTPException(422, "Deferred labels require a reason")
    if set(body.labels) != LABEL_FIELDS:
        raise HTTPException(422, "All evaluation label fields are required")


@router.put("/candidates/{split}/{sample_id}")
async def save_label(split: str, sample_id: str, body: LabelBody,
                     principal: Principal = Depends(get_principal)):  # noqa: B008
    if not await _allowed(principal):
        raise HTTPException(403, "Insufficient role")
    _validate_labels(split, sample_id, body)
    await _record(principal, split, sample_id, body, "evaluation_label")
    return {"id": sample_id, "status": body.status}


@router.post("/candidates/{split}/{sample_id}/consensus")
async def confirm_consensus(split: str, sample_id: str, body: LabelBody,
                            principal: Principal = Depends(get_principal)):  # noqa: B008
    if not await _allowed(principal):
        raise HTTPException(403, "Insufficient role")
    _validate_labels(split, sample_id, body)
    labels = _latest_by_user(await _labels(principal.tenant_id, split))
    votes = [x for x in labels if x["id"] == sample_id and x["status"] == "confirmed"]
    if len({x["user_id"] for x in votes}) < 2 or consensus_state([x["labels"] for x in votes]) != "consensus_required":
        raise HTTPException(409, "A disagreement between two labelers is required")
    agreed = LabelBody(labels=body.labels, confidence=body.confidence)
    await _record(principal, split, sample_id, agreed, "evaluation_consensus_confirmed")
    return {"id": sample_id, "status": "confirmed", "consensus": "resolved"}
