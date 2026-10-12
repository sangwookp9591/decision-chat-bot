"""Decision cases: reviewer classification judgments kept with provenance and
reused as advisory precedents in later reviews.

A case never changes a judgment or grants an action. It is shown to a reviewer,
who decides. Fields come only from the stored Correction (AI value, reviewer
value, reviewer reason) or from an explicit reviewer edit (conditions,
exceptions, outcome); nothing is inferred.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from ildongi.auth.policy import can
from ildongi.auth.types import Principal
from ildongi.db.audit import append_audit_in_tx
from ildongi.db.tx import read_tx, write_tx
from ildongi.domain.ids import new_id
from ildongi.domain.masking import mask_for_external
from ildongi.domain.rules import normalize_for_match, text_matches
from ildongi.policy.service import DEFAULT_CONFIG

FIELDS = ("ai_need", "feasibility", "urgency", "lead_org")
STATUSES = ("recorded", "confirmed", "verified", "retired")
# ponytail: fixed horizon; move to Dynamic Config when a tenant needs another one.
STALE_DAYS = 180
PER_FIELD = 3
_APPLICABILITY_RANK = {"applies": 0, "unconfirmed": 1, "excepted": 2}
_STATUS_RANK = {"verified": 0, "confirmed": 1, "recorded": 2}


class CaseError(Exception):
    def __init__(self, message: str, status_code: int = 422):
        self.status_code = status_code
        super().__init__(message)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _decode(value: Any, default: Any) -> Any:
    if value is None:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _time(value: Any) -> datetime | None:
    if value is None:
        return None
    native = value.to_native() if hasattr(value, "to_native") else value
    return native if native.tzinfo else native.replace(tzinfo=UTC)


def keywords(values: Any) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list) or len(values) > 20:
        raise CaseError("조건·예외 키워드는 20개 이하 목록이어야 합니다")
    out: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise CaseError("키워드는 문자열이어야 합니다")
        value = value.strip()
        if not 1 <= len(normalize_for_match(value)[0]) <= 50:
            raise CaseError("키워드는 공백을 뺀 1–50자여야 합니다")
        if value not in out:
            out.append(value)
    return out


def assess(case: dict, text: str, now: datetime) -> dict:
    """Decide whether a case can be reused for the current request text."""
    units = [{"unit_id": "request", "text": text or ""}]
    exceptions, conditions = case.get("exceptions") or [], case.get("conditions") or []
    hit = text_matches({"text": {"contains_any": exceptions}}, units, 1) if exceptions else []
    if hit:
        applicability, keyword = "excepted", hit[0]["keyword"]
    elif not conditions:
        applicability, keyword = "unconfirmed", None
    else:
        hit = text_matches({"text": {"contains_any": conditions}}, units, 1)
        applicability, keyword = ("applies", hit[0]["keyword"]) if hit else ("unmet", None)
    updated = _time(case.get("updated_at"))
    age_days = (now - updated).days if updated else None
    return {"applicability": applicability, "matched_keyword": keyword,
            "age_days": age_days, "stale": age_days is not None and age_days > STALE_DAYS}


def _visible(principal: Principal, case: dict) -> bool:
    return can(principal, "rule:read", {"tenant_id": case.get("tenant_id"),
                                        "org_ids": case.get("org_ids") or []})


def _public(node: Any) -> dict:
    case = {"outcome": None, "outcome_note": None, **dict(node)}
    for key in ("ai_value", "corrected_value"):
        case[key] = _decode(case.get(key), None)
    for key in ("conditions", "exceptions", "history"):
        case[key] = _decode(case.get(key), [])
    return case


def _out(case: dict) -> dict:
    data = {k: v for k, v in case.items() if k not in {"tenant_id", "org_ids"}}
    for key in ("created_at", "updated_at"):
        if data.get(key) is not None:
            data[key] = str(data[key])
    return data


async def create_cases_in_tx(tx, tenant: str, request: dict, decision_id: str,
                             corrections: list[tuple[str, str, Any, Any]], reason: str,
                             actor: str) -> list[str]:
    """Record one case per corrected classification in the review transaction."""
    reason = mask_for_external(reason, DEFAULT_CONFIG)
    org_ids = sorted(set(request.get("org_ids") or []) | set(request.get("shared_org_ids") or []))
    ids = []
    for correction_id, field, old, new in corrections:
        if field not in FIELDS:
            continue
        case_id = new_id("case")
        history = [{"version": 1, "action": "recorded", "status": "recorded", "by": actor,
                    "at": datetime.now(UTC).isoformat(), "conditions": [], "exceptions": [],
                    "outcome": None, "outcome_note": None, "note": None}]
        await (await tx.run(
            "MATCH (c:Correction {tenant_id:$tenant,id:$correction}) "
            "CREATE (k:DecisionCase {id:$id,tenant_id:$tenant,field:$field,"
            "ai_value:$ai,corrected_value:$corrected,reason:$reason,situation:$situation,"
            "request_id:$request,run_id:c.run_id,revision_id:c.revision_id,"
            "correction_id:$correction,review_decision_id:$decision,org_ids:$orgs,"
            "owner:$actor,status:'recorded',conditions:'[]',exceptions:'[]',"
            "outcome:null,outcome_note:null,version:1,history:$history,"
            "consulted:0,followed:0,created_at:datetime(),updated_at:datetime(),updated_by:$actor}) "
            "CREATE (k)-[:FROM]->(c)",
            tenant=tenant, correction=correction_id, id=case_id, field=field,
            ai=_json(old), corrected=_json(new), reason=reason,
            situation=request.get("title") or "", request=request.get("id"),
            decision=decision_id, orgs=org_ids, actor=actor, history=_json(history),
        )).consume()
        ids.append(case_id)
    return ids


async def record_consultations_in_tx(tx, tenant: str, decision_id: str,
                                     case_ids: list[str], final: dict) -> None:
    """Store whether the reviewer's final value followed each shown precedent."""
    for case_id in dict.fromkeys(case_ids):
        row = await (await tx.run(
            "MATCH (k:DecisionCase {tenant_id:$tenant,id:$id}) RETURN k",
            tenant=tenant, id=case_id,
        )).single()
        if row is None:
            continue
        case = _public(row["k"])
        followed = final.get(case["field"]) == case["corrected_value"]
        await (await tx.run(
            "MATCH (k:DecisionCase {tenant_id:$tenant,id:$id}) "
            "MATCH (h:ReviewDecision {tenant_id:$tenant,id:$decision}) "
            "CREATE (h)-[:CONSULTED {followed:$followed,case_version:k.version}]->(k) "
            "SET k.consulted=k.consulted+1,k.followed=k.followed+$inc",
            tenant=tenant, id=case_id, decision=decision_id, followed=followed,
            inc=int(followed),
        )).consume()


async def _live_cases(tenant: str, exclude_request: str | None = None) -> list[dict]:
    # A case whose source Correction was deleted is never reused.
    async def op(tx):
        rows = await (await tx.run(
            "MATCH (k:DecisionCase {tenant_id:$tenant})-[:FROM]->(:Correction {tenant_id:$tenant}) "
            "WHERE $request IS NULL OR k.request_id<>$request "
            "RETURN k ORDER BY k.updated_at DESC LIMIT 500",
            tenant=tenant, request=exclude_request,
        )).data()
        return [_public(row["k"]) for row in rows]
    return await read_tx(tenant, op)


async def precedents(principal: Principal, request_id: str, judgment: dict | None,
                     text: str | None, now: datetime | None = None) -> dict:
    """Visible, applicable precedents for each classification of a request."""
    now = now or datetime.now(UTC)
    judgment = judgment or {}
    result = {field: {"items": [], "conflict": False, "hidden_unmet": 0} for field in FIELDS}
    for case in await _live_cases(principal.tenant_id, request_id):
        field = case["field"]
        if (case["status"] == "retired" or field not in result
                or case["ai_value"] != judgment.get(field) or not _visible(principal, case)):
            continue
        verdict = assess(case, text or "", now)
        if verdict["applicability"] == "unmet":
            result[field]["hidden_unmet"] += 1
            continue
        if not principal.can_read_source:
            verdict["matched_keyword"] = None
        item = _out(case)
        item.pop("history", None)
        result[field]["items"].append({**item, **verdict})
    for entry in result.values():
        entry["items"].sort(key=lambda i: (_APPLICABILITY_RANK[i["applicability"]],
                                           _STATUS_RANK.get(i["status"], 3), i["stale"],
                                           i["age_days"] or 0))
        entry["items"] = entry["items"][:PER_FIELD]
        values = {_json(i["corrected_value"]) for i in entry["items"]
                  if i["applicability"] != "excepted"}
        entry["conflict"] = len(values) > 1
    return result


async def list_cases(principal: Principal, status: str | None = None,
                     field: str | None = None) -> list[dict]:
    return [_out(case) for case in await _live_cases(principal.tenant_id)
            if _visible(principal, case)
            and (status is None or case["status"] == status)
            and (field is None or case["field"] == field)]


async def change_case(principal: Principal, case_id: str, action: str, body: dict) -> dict:
    if not can(principal, "learn_propose", {"tenant_id": principal.tenant_id}):
        raise CaseError("사례를 수정할 권한이 없습니다", 403)
    tenant = principal.tenant_id

    async def op(tx):
        row = await (await tx.run(
            "MATCH (k:DecisionCase {tenant_id:$tenant,id:$id}) RETURN k",
            tenant=tenant, id=case_id,
        )).single()
        if row is None or not _visible(principal, case := _public(row["k"])):
            raise CaseError("사례를 찾을 수 없습니다", 404)
        if body.get("version") != case["version"]:
            raise CaseError("사례가 먼저 변경되었습니다. 새로고침 후 다시 시도하세요", 409)
        state = {k: case.get(k) for k in ("status", "conditions", "exceptions", "outcome", "outcome_note")}
        note = (body.get("reason") or body.get("note") or "").strip()
        if action == "confirm":
            if case["status"] == "retired":
                raise CaseError("폐기된 사례는 되돌린 뒤 확인하세요", 409)
            conditions = keywords(body.get("conditions"))
            if not conditions:
                raise CaseError("적용 조건 키워드가 하나 이상 필요합니다")
            state.update(conditions=conditions, exceptions=keywords(body.get("exceptions")),
                         status="verified" if case["status"] == "verified" else "confirmed")
        elif action == "outcome":
            if body.get("outcome") not in {"held", "failed"} or not note:
                raise CaseError("결과(held·failed)와 확인 내용이 필요합니다")
            state.update(outcome=body["outcome"], outcome_note=note,
                         status="verified" if body["outcome"] == "held" else "retired")
        elif action == "retire":
            if not note:
                raise CaseError("폐기 사유가 필요합니다")
            state.update(status="retired")
        elif action == "revert":
            target = next((h for h in case["history"] if h["version"] == body.get("to_version")), None)
            if target is None or target["version"] == case["version"]:
                raise CaseError("되돌릴 버전을 찾을 수 없습니다")
            state.update(status=target["status"], conditions=target["conditions"],
                         exceptions=target["exceptions"], outcome=target["outcome"],
                         outcome_note=target.get("outcome_note"))
            note = note or f"v{target['version']}로 되돌림"
        else:
            raise CaseError("알 수 없는 동작입니다", 404)
        version = case["version"] + 1
        history = [*case["history"], {
            "version": version, "action": action, "status": state["status"],
            "by": principal.user_id, "at": datetime.now(UTC).isoformat(),
            "conditions": state["conditions"], "exceptions": state["exceptions"],
            "outcome": state["outcome"], "outcome_note": state["outcome_note"], "note": note,
        }]
        await (await tx.run(
            "MATCH (k:DecisionCase {tenant_id:$tenant,id:$id}) "
            "SET k.status=$status,k.conditions=$conditions,k.exceptions=$exceptions,"
            "k.outcome=$outcome,k.outcome_note=$outcome_note,k.version=$version,"
            "k.history=$history,k.updated_at=datetime(),k.updated_by=$actor",
            tenant=tenant, id=case_id, status=state["status"],
            conditions=_json(state["conditions"]), exceptions=_json(state["exceptions"]),
            outcome=state["outcome"], outcome_note=state["outcome_note"], version=version,
            history=_json(history), actor=principal.user_id,
        )).consume()
        await append_audit_in_tx(tx, tenant, principal.user_id, f"case.{action}", "DecisionCase",
                                 case_id, {"version": case["version"], "status": case["status"]},
                                 {"version": version, "status": state["status"]}, note or action)
        return {**_out({**case, **state, "version": version, "history": history}),
                "updated_by": principal.user_id}
    return await write_tx(tenant, op)
