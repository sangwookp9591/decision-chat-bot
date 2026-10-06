from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

from ildongi.auth.core import Principal
from ildongi.auth.policy import can
from ildongi.evaluation.store import labels_for_split, record_label

ROOT = Path(__file__).resolve().parents[3]
LABEL_FIELDS = {"ai_need", "feasibility", "urgency", "team_set", "risk_areas"}
LABEL_OPTIONS = {
    # Single-choice fields also accept the uncertain answer the labeling UI offers.
    "ai_need": {"필요", "불필요", "혼합", "정보 부족"},
    "feasibility": {"가능", "조건부 가능", "현재 불가", "정보 부족"},
    "urgency": {"긴급", "일반", "판단 보류"},
    "team_set": {"AI팀", "IT팀", "현업"},
    "risk_areas": {"임상·안전성 검토", "약물감시 검토", "규제 검토"},
}
SET_FIELDS = {"team_set", "risk_areas"}


def normalize_labels(labels: dict[str, Any]) -> dict[str, Any]:
    return {key: sorted(set(value)) if key in SET_FIELDS else value for key, value in labels.items()}


def consensus_state(labels: list[dict[str, Any]]) -> str:
    if not labels:
        return "unlabeled"
    if len(labels) == 1:
        return "single_label"
    signatures = [json.dumps(normalize_labels(x), sort_keys=True, ensure_ascii=False) for x in labels]
    return "agreed" if len(set(signatures)) == 1 else "consensus_required"


def progress_summary(total: int, labels: list[dict[str, Any]]) -> dict[str, int]:
    latest: dict[str, str] = {}
    for item in labels:
        latest[item["id"]] = item["status"]
    confirmed = sum(status in {"confirmed", "consensus_confirmed"} for status in latest.values())
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
    return await labels_for_split(tenant, split)


def _latest_by_user(labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for item in labels:
        latest[(item["id"], item["user_id"])] = {**item, "labels": json.loads(item["labels"])}
    return list(latest.values())


async def candidates(split: str, principal: Principal):
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
    await record_label(
        principal.tenant_id, split, sample_id, principal.user_id, body.labels,
        "consensus_confirmed" if action == "evaluation_consensus_confirmed" else body.status,
        body.reason, body.confidence, action,
    )


def _validate_labels(split: str, sample_id: str, body: LabelBody) -> None:
    if not any(x["id"] == sample_id for x in _rows(split)):
        raise HTTPException(404, "Sample not found")
    if body.status not in {"confirmed", "deferred"} or (body.status == "deferred" and not body.reason):
        raise HTTPException(422, "Deferred labels require a reason")
    errors: dict[str, str] = {}
    for field in LABEL_FIELDS - set(body.labels):
        errors[field] = "필수 필드입니다."
    for field in set(body.labels) - LABEL_FIELDS:
        errors[field] = "알 수 없는 필드입니다."
    for field in LABEL_FIELDS & set(body.labels):
        value = body.labels[field]
        if field in SET_FIELDS:
            if not isinstance(value, list):
                errors[field] = "허용된 값의 배열이어야 합니다."
            elif any(not isinstance(item, str) or item not in LABEL_OPTIONS[field] for item in value):
                errors[field] = "배열의 모든 값은 허용된 선택지여야 합니다."
        elif not isinstance(value, str) or value not in LABEL_OPTIONS[field]:
            errors[field] = "허용된 선택지 중 하나를 선택해야 합니다."
    if errors:
        raise HTTPException(422, {"message": "평가 라벨이 올바르지 않습니다.", "details": {"fields": errors}})
    body.labels = normalize_labels(body.labels)


async def save_label(split: str, sample_id: str, body: LabelBody,
                     principal: Principal):
    if not await _allowed(principal):
        raise HTTPException(403, "Insufficient role")
    _validate_labels(split, sample_id, body)
    await _record(principal, split, sample_id, body, "evaluation_label")
    return {"id": sample_id, "status": body.status}


async def confirm_consensus(split: str, sample_id: str, body: LabelBody,
                            principal: Principal):
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
