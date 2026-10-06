"""Deterministic, side effect free application of approved rules."""
from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

TARGETS = {"lead_org", "collab_orgs", "review_route", "ai_need", "feasibility", "urgency"}
CLASS_VALUES = {
    "ai_need": {"필요", "불필요", "혼합", "정보 부족"},
    "feasibility": {"가능", "조건부 가능", "현재 불가", "정보 부족"},
    "urgency": {"긴급", "일반", "판단 보류"},
}
ORGANIZATIONS = {"AI팀", "IT팀", "현업"}


class RuleInvariantError(ValueError):
    """An action could weaken a server enforced review or assignment rule."""


def validate_rule_or_raise(body: dict[str, Any]) -> dict[str, Any]:
    """Validate a rule and preserve the invariant versus schema error distinction."""
    try:
        return validate_rule(body)
    except RuleInvariantError:
        raise
    except (ValueError, TypeError) as exc:
        raise ValueError(str(exc)) from exc


def validate_rule(body: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(body, dict) or body.get("schema") != "rule-v1":
        raise ValueError("rule schema must be rule-v1")
    if not isinstance(body.get("rule_id"), str) or not re.fullmatch(r"R-[A-Z_]+-[0-9]{2,}", body["rule_id"]) or not isinstance(body.get("version"), int) or isinstance(body["version"], bool) or body["version"] < 1:
        raise ValueError("invalid rule identity")
    if body.get("effect") not in {"rule", "context"}:
        raise ValueError("invalid effect")
    if body.get("target") not in TARGETS:
        raise RuleInvariantError("target is outside the safety allowlist")
    scope = body.get("scope")
    if not isinstance(scope, dict) or set(scope) != {"all"} or not isinstance(scope["all"], list):
        raise ValueError("scope.all is required")
    for clause in scope["all"]:
        if not isinstance(clause, dict):
            raise ValueError("invalid scope clause")  # noqa: TRY004 - callers map ValueError to RULE_INVALID (422)
        if "field" in clause:
            if set(clause) != {"field", "op", "value"} or clause["field"] not in {"ai_need", "feasibility", "urgency", "lead_org"} or clause["op"] not in {"eq", "in"}:
                raise ValueError("invalid field predicate")
            if clause["op"] == "in" and (not isinstance(clause["value"], list) or not clause["value"]):
                raise ValueError("in predicate needs values")
        elif "signal" in clause:
            if set(clause) != {"signal", "op", "value"} or clause["op"] not in {"gte", "lte"} or not isinstance(clause["signal"], str) or not isinstance(clause["value"], (int, float)) or not 0 <= clause["value"] <= 1:
                raise ValueError("invalid signal predicate")
        elif "catalog_task" in clause:
            if set(clause) != {"catalog_task", "present"} or not isinstance(clause["catalog_task"], str) or not isinstance(clause["present"], bool):
                raise ValueError("invalid catalog predicate")
        elif "requester_org" in clause:
            if set(clause) != {"requester_org"} or not isinstance(clause["requester_org"], str):
                raise ValueError("invalid requester org predicate")
        else:
            raise ValueError("unsupported scope predicate")
    if body["effect"] == "context" and any("requester_org" not in clause for clause in scope["all"]):
        raise ValueError("context scope must be decidable before Decision AI")
    action = body.get("action")
    if not isinstance(action, dict) or len(action) != 1:
        raise RuleInvariantError("exactly one allowed action is required")
    target = body["target"]
    if "require_review" in action:
        if not isinstance(action["require_review"], str) or not action["require_review"].strip():
            raise ValueError("review reason is required")
        if target not in {"urgency", "review_route"}:
            raise RuleInvariantError("require_review is only valid for urgency or review_route")
    elif "add" in action:
        if target != "collab_orgs" or not isinstance(action["add"], str) or action["add"] not in ORGANIZATIONS:
            raise RuleInvariantError("collab_orgs must add a known organization")
    elif "set" in action:
        value = action["set"]
        allowed = {"urgency": {"긴급"}, "feasibility": CLASS_VALUES["feasibility"] - {"가능"},
                   "ai_need": CLASS_VALUES["ai_need"], "lead_org": ORGANIZATIONS}
        if target not in allowed or not isinstance(value, str) or value not in allowed[target]:
            raise RuleInvariantError("action is outside the target safety allowlist")
    else:
        raise RuleInvariantError("unsupported action")
    if body["effect"] == "context":
        if not isinstance(body.get("context_text"), str) or not body["context_text"].strip() or len(body["context_text"]) > 500:
            raise ValueError("context_text is required and limited to 500 characters")
    elif body.get("context_text"):
        raise ValueError("context_text is only valid for context rules")
    return body


def _matches(clause: dict, result: dict, features: dict) -> bool:
    classes = result.get("classifications", {})
    if "field" in clause:
        value = classes.get(clause["field"])
        return value == clause["value"] if clause["op"] == "eq" else value in clause["value"]
    if "signal" in clause:
        value = features.get("signals", {}).get(clause["signal"])
        return isinstance(value, (int, float)) and (value >= clause["value"] if clause["op"] == "gte" else value <= clause["value"])
    if "catalog_task" in clause:
        found = any(task.get("catalog_task_id", task.get("type_id")) == clause["catalog_task"] for task in result.get("draft_tasks", []))
        return found == clause["present"]
    return clause["requester_org"] in features.get("requester_orgs", [])


def apply_rules(judgment_result: dict, rules_snapshot: list[dict], *, features: dict | None = None) -> tuple[dict, list[dict]]:
    result = deepcopy(judgment_result)
    features = features or {}
    applications: list[dict] = []
    winners: dict[str, int] = {}
    for reference in rules_snapshot:
        body = {"schema": "rule-v1", **reference.get("body", reference)}
        rule_version = f"{body['rule_id']}@{body['version']}"
        target = body["target"]
        before = deepcopy(result.get("classifications", {}).get(target) if target in CLASS_VALUES or target == "lead_org" else result.get(target))
        if target == "collab_orgs" and before is None:
            before = sorted({org for task in result.get("draft_tasks", [])
                             for org in task.get("collab_orgs", [])})
        application = {"rule_version": rule_version, "effect": body["effect"],
                       "outcome": "out_of_scope", "before": before, "after": before}
        applications.append(application)
        try:
            validate_rule(body)
        except (ValueError, TypeError):
            application["outcome"] = "blocked_by_invariant"
            continue
        if not all(_matches(clause, result, features) for clause in body["scope"]["all"]):
            continue
        action = body["action"]
        original = judgment_result.get("classifications", {})
        if (target == "urgency" and original.get("urgency") == "긴급"
                and action.get("set") not in (None, "긴급")):
            application["outcome"] = "blocked_by_invariant"
            continue
        previous = winners.get(target)
        if body["effect"] == "context":
            application["outcome"] = "used"
            application["after"] = body["context_text"]
            continue
        if previous is not None:
            old = applications[previous]
            old_action = rules_snapshot[previous].get("body", rules_snapshot[previous])["action"]
            if "require_review" in old_action and "require_review" not in action:
                application["outcome"] = "conflict"
                continue
            old["outcome"] = "conflict"
            if "require_review" in old_action:
                reasons = result.get("rule_review_reasons", [])
                if old_action["require_review"] in reasons:
                    reasons.remove(old_action["require_review"])
        winners[target] = len(applications) - 1
        if "require_review" in action:
            reasons = result.setdefault("rule_review_reasons", [])
            if action["require_review"] not in reasons:
                reasons.append(action["require_review"])
            application["after"] = action["require_review"]
        elif "add" in action:
            orgs = result.setdefault("collab_orgs", before[:])
            if action["add"] not in orgs:
                orgs.append(action["add"])
            for task in result.get("draft_tasks", []):
                task_orgs = task.setdefault("collab_orgs", [])
                if action["add"] not in task_orgs:
                    task_orgs.append(action["add"])
            application["after"] = deepcopy(orgs)
        else:
            result.setdefault("classifications", {})[target] = action["set"]
            if target == "lead_org":
                for task in result.get("draft_tasks", []):
                    task["lead_org"] = action["set"]
            application["after"] = action["set"]
        application["outcome"] = "used"
    result["rule_effects"] = applications
    return result, applications
