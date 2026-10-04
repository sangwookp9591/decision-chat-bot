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


def consensus_state(labels: list[dict[str, Any]]) -> str:
    if len(labels) < 2:
        return "single_label" if labels else "unlabeled"
    return "agreed" if all(x == labels[0] for x in labels[1:]) else "consensus_required"


def visible_candidate(row: dict[str, Any], split: str) -> dict[str, Any]:
    result = dict(row)
    if split == "final":
        result.pop("predictions", None)
        result.pop("model_result", None)
    return result


def _rows(split: str) -> list[dict[str, Any]]:
    if split not in {"tuning", "final"}:
        raise HTTPException(422, "Unknown split")
    path = ROOT / "eval/candidates" / f"{split}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


async def _allowed(principal: Principal) -> bool:
    return can(principal, "eval_label", {"tenant_id": principal.tenant_id})


@router.get("/candidates")
async def candidates(split: str = "tuning", principal: Principal = Depends(get_principal)):  # noqa: B008
    if not await _allowed(principal):
        raise HTTPException(403, "Insufficient role")
    rows = _rows(split)
    async def op(tx):
        return await (await tx.run(
            "MATCH (l:EvalLabel {tenant_id:$tenant,split:$split}) RETURN l.sample_id AS id,"
            "l.labels AS labels,l.status AS status,l.user_id AS user_id,l.created_at AS created_at",
            tenant=principal.tenant_id, split=split)).data()
    labels = await read_tx(principal.tenant_id, op)
    by_id: dict[str, list[dict[str, Any]]] = {}
    for item in labels:
        by_id.setdefault(item["id"], []).append(item)
    return {"split": split, "candidates": [visible_candidate({**row, "labels": by_id.get(row["id"], []),
            "consensus": consensus_state([json.loads(x["labels"]) for x in by_id.get(row["id"], [])])}, split)
            for row in rows]}


class LabelBody(BaseModel):
    labels: dict[str, Any] = Field(...)
    status: str = "confirmed"
    reason: str | None = None
    confidence: float = Field(ge=0, le=1)


@router.put("/candidates/{split}/{sample_id}")
async def save_label(split: str, sample_id: str, body: LabelBody,
                     principal: Principal = Depends(get_principal)):  # noqa: B008
    if not await _allowed(principal):
        raise HTTPException(403, "Insufficient role")
    rows = _rows(split)
    if not any(x["id"] == sample_id for x in rows):
        raise HTTPException(404, "Sample not found")
    if body.status not in {"confirmed", "deferred"} or (body.status == "deferred" and not body.reason):
        raise HTTPException(422, "Deferred labels require a reason")
    expected = {"ai_need", "feasibility", "urgency", "team_set", "risk_areas"}
    if set(body.labels) != expected:
        raise HTTPException(422, "All evaluation label fields are required")
    async def store(tx):
        await (await tx.run(
            "CREATE (l:EvalLabel {tenant_id:$tenant,split:$split,sample_id:$id,user_id:$user,"
            "labels:$labels,status:$status,reason:$reason,confidence:$confidence,created_at:datetime()}) "
            "CREATE (a:AuditEvent {tenant_id:$tenant,kind:'evaluation_label',actor:$user,"
            "subject:$id,action:$status,reason:$reason,created_at:datetime()})",
            tenant=principal.tenant_id, split=split, id=sample_id, user=principal.user_id,
            labels=json.dumps(body.labels, ensure_ascii=False), status=body.status,
            reason=body.reason, confidence=body.confidence)).consume()
    await write_tx(principal.tenant_id, store)
    return {"id": sample_id, "status": body.status}
