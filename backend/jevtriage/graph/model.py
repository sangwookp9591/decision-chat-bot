"""Judgment graph vocabulary: layers, node kinds, and real relationship types only.

Edge direction is stored as written by the producing modules. ``upstream`` always means
toward the evidence side and ``downstream`` toward execution; ``PUBLISHED_IN`` is the only
relationship whose stored source is the upstream endpoint.
"""
from __future__ import annotations

import json
from typing import Any

LAYERS: dict[int, dict[str, str]] = {
    1: {"name": "근거", "desc": "문서 구간 · 모델 반환값 · 사람 수정"},
    2: {"name": "가설", "desc": "근거에서 나온 규칙 후보"},
    3: {"name": "판단", "desc": "요청 검토 결정 · 후보 승인·기각"},
    4: {"name": "적용", "desc": "규칙·Config 버전 · 검증 · 상태"},
    5: {"name": "업무 단계", "desc": "판단과 규칙을 실제로 쓴 실행 단계"},
}
KIND_LAYER: dict[str, int] = {
    "EvidenceSpan": 1, "ModelOutput": 1, "Correction": 1, "RuleCandidate": 2,
    "RuleDecision": 3, "ReviewDecision": 3, "RuleVersion": 4, "ValidationRun": 4,
    "ConfigVersion": 4, "RunStep": 5,
}
KINDS = tuple(KIND_LAYER)
# Relationship types allowed in this graph; stored orientation is (source)-[type]->(target).
UP_TYPES = ("CITES", "CORRECTS", "RECORDED", "SUPPORTED_BY", "DECIDES", "DERIVED_FROM",
            "VALIDATES", "APPLIED", "USED_OUTPUT")  # target is the upstream endpoint
FORWARD_UP_TYPES = ("PUBLISHED_IN",)  # source is the upstream endpoint
EDGE_TYPES = UP_TYPES + FORWARD_UP_TYPES
UP_TYPE_PATTERN = "|".join(UP_TYPES)
MAX_DEPTH = 8
NODE_CAP = 400

_JSON_FIELDS = ("ai_value", "corrected_value", "probabilities", "legend", "location_json",
                "body", "confirmed_scope", "proposed_body", "uncertainty", "versions_json",
                "before", "after")


def edge_id(kind: str, source: str, target: str) -> str:
    return f"{kind}:{source}->{target}"


def _decode(value: Any) -> Any:
    if isinstance(value, str) and value[:1] in "{[":
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


decode_value = _decode


def _text(value: Any) -> str:
    value = _decode(value)
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _short(value: str, limit: int = 40) -> str:
    return value if len(value) <= limit else value[: limit - 1] + "…"


def describe(kind: str, p: dict[str, Any]) -> dict[str, Any]:
    """Return a presentation record built only from stored properties."""
    status = p.get("status")
    out: dict[str, Any] = {"title": p.get("id"), "summary": "", "actor": None, "at": None,
                           "version": None, "status": status, "source": None}
    if kind == "EvidenceSpan":
        loc = _decode(p.get("location_json")) or {}
        place = " ".join(str(v) for v in loc.values()) if isinstance(loc, dict) else _text(loc)
        out.update(title=_short(f"문서 근거 {place}".strip(), 48), summary=f"원문 위치 {place}".strip(),
                   actor="— (관찰 사실)", at=None, version=p.get("revision_id"),
                   source=p.get("attachment_id") or p.get("revision_id"), status="보존")
    elif kind == "ModelOutput":
        conf = p.get("confidence")
        value = _text(p.get("value") if p.get("value") is not None else p.get("noul"))
        out.update(title=_short(f"Jev · {p.get('question_id')}"), summary=f"{p.get('type')}: {_short(value, 120)}"
                   + (f", confidence {conf}" if conf is not None else ""),
                   actor=f"Jev {p.get('model') or ''}".strip(), version=p.get("model"),
                   source=p.get("run_id"), status="원안 보존")
    elif kind == "Correction":
        out.update(title=_short(f"수정 · {p.get('field')}"),
                   summary=f"{p.get('field')}: {_short(_text(p.get('ai_value')), 60)} → {_short(_text(p.get('corrected_value')), 60)}"
                   + (f". 사유: {p['reason']}" if p.get("reason") else ""),
                   actor=p.get("corrected_by"), at=p.get("corrected_at"),
                   version=f"config v{p.get('config_version')}" if p.get("config_version") is not None else None,
                   source=p.get("review_id"), status="요청 한 건에만 적용")
    elif kind == "RuleCandidate":
        body = _decode(p.get("proposed_body")) or {}
        action = body.get("action") if isinstance(body, dict) else None
        out.update(title=_short(f"후보 · {p.get('field')}"), summary=f"{p.get('field')} → {_text(action)}",
                   actor=p.get("author"), at=p.get("created_at"), version=p.get("id"),
                   source=f"{p.get('source')} 가설")
    elif kind == "RuleDecision":
        out.update(title=_short(f"규칙 결정 · {p.get('action')}"),
                   summary=f"{p.get('action')}. 사유: {p.get('reason') or '—'}. 확정 범위 {_text(p.get('confirmed_scope'))}",
                   actor=p.get("decided_by"), at=p.get("decided_at"), version=p.get("id"),
                   status=p.get("action"))
    elif kind == "ReviewDecision":
        out.update(title=_short(f"검토 결정 · {p.get('action')}"),
                   summary=f"{p.get('action')}. 사유: {p.get('reason') or '—'}",
                   actor=p.get("actor_id"), at=p.get("created_at"),
                   version=f"review v{p.get('review_version')}", source=p.get("review_id"),
                   status="확정 · 공통 규칙 아님")
    elif kind == "RuleVersion":
        body = _decode(p.get("body")) or {}
        out.update(title=p.get("id"),
                   summary=f"효과 {body.get('effect')} · 대상 {body.get('target')} · 범위 {_text(body.get('scope'))} · 동작 {_text(body.get('action'))}",
                   at=p.get("created_at"), version=f"{p.get('rule_id')}@{p.get('version')}",
                   source="규칙 버전")
    elif kind == "ValidationRun":
        out.update(title=_short(f"검증 {p.get('id')}"),
                   summary=f"부작용 {p.get('side_effects', '—')}건 · 표본 {p.get('sample_count', '—')}",
                   actor=p.get("created_by"), at=p.get("created_at"), version=p.get("candidate_config_version"))
    elif kind == "ConfigVersion":
        out.update(title=f"Config v{p.get('version')}", summary=p.get("reason") or "",
                   actor=p.get("created_by"), at=p.get("created_at"), version=f"v{p.get('version')}",
                   source="Dynamic Config")
    elif kind == "RunStep":
        out.update(title=_short(f"{p.get('name')}"), summary=f"{p.get('kind')} 단계 · {p.get('status')}",
                   actor=p.get("actor"), at=p.get("started_at"), version=_text(_decode(p.get("versions_json"))),
                   source=f"{p.get('run_id')} · {p.get('id')}")
    if out["at"] is not None:
        out["at"] = str(out["at"])
    out["status"] = None if out["status"] is None else str(out["status"])
    return out
