"""Conservative, server-owned automatic assignment gate."""
from __future__ import annotations

NEVER_ASSIGN = {"조건부 가능", "현재 불가", "정보 부족", "판단 보류", "미정", None}
from .questions import CLASS_KEYS, ORG_KEYS, RISK_KEYS

CLASSIFICATIONS = CLASS_KEYS


def evaluate_auto_assign(judgment: dict, policy: dict, context: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    for key, label in (("input_confirmed", "입력 확정 미완료"),
                       ("latest_run", "최신 실행 아님"),
                       ("evidence_complete", "근거 미완료")):
        if not context.get(key, False):
            reasons.append(label)
    if judgment.get("feasibility") != "가능":
        reasons.append("개발 가능성 미충족")
    for key in CLASSIFICATIONS:
        if judgment.get(key) in NEVER_ASSIGN:
            reasons.append(f"미정 분류: {key}")
        confidence = judgment.get("choice_confidences", {}).get(key)
        threshold = policy.get("choice_confidence_thresholds", {}).get(key)
        if threshold is None or confidence is None or confidence < threshold:
            reasons.append(f"Choice confidence 미충족: {key}")
    if judgment.get("urgency") == "긴급":
        reasons.append("필수 검토: urgent")
    risk_clear_max = policy.get("risk_clear_max", 0.2)
    risk_signals = judgment.get("risk_signals", {})
    risk_confirmed = all(
        isinstance(risk_signals.get(key), (int, float))
        and risk_signals[key] <= risk_clear_max
        for key in RISK_KEYS
    )
    if not risk_confirmed or judgment.get("risk_confirmed") is not True:
        reasons.append("필수 검토: 위험 여부 미확정")
    for key in RISK_KEYS:
        if risk_signals.get(key, 1) > risk_clear_max:
            reasons.append(f"필수 검토: {key}")
    band = policy.get("noul_uncertain_band", [0.35, 0.65])
    if not isinstance(band, (list, tuple)) or len(band) != 2 or not 0 <= band[0] <= band[1] <= 1:
        band = [0, 1]
    for key in ORG_KEYS:
        value = judgment.get("signals", {}).get(key)
        if value is None or band[0] <= value <= band[1]:
            reasons.append(f"Noul 참여 불확실: {key}")
    tasks = judgment.get("draft_tasks") or []
    if not tasks:
        reasons.append("업무 초안 없음")
    if any(
        not t.get("lead_org") or t.get("lead_org") == "미정"
        or not t.get("deliverable") or t.get("status") in {"미정", "undetermined"}
        for t in tasks
    ):
        reasons.append("업무 책임 또는 산출물 누락")
    if not policy.get("auto_assign", False):
        reasons.append("정책에서 자동 배정 비허용")
    if context.get("already_assigned"):
        reasons.append("기존 배정 있음")
    return not reasons, reasons
