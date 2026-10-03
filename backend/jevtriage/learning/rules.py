"""Tenant scoped rule decisions, validation, and atomic Config publication."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from jevtriage.db.audit import append_audit_in_tx
from jevtriage.db.events import append_event_in_tx
from jevtriage.db.idempotency import IdempotencyConflict, get_or_create_in_tx
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.domain.ids import new_id
from jevtriage.learning.apply import RuleInvariantError, validate_rule
from jevtriage.policy.service import (
    DEFAULT_CONFIG,
    PolicyError,
    publish_config_in_tx,
    validate_config,
)

RULE_ID = re.compile(r"^R-[A-Z_]+-[0-9]{2,}$")
RULE_REFERENCE_FIELDS = ("rule_id", "version", "effect", "target", "scope", "action", "context_text", "candidate_id", "decision_id")
INSUFFICIENT_APPROVAL_LABEL = "자료 부족 상태로 승인됨"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _reason(reason: str) -> str:
    if not reason or not reason.strip():
        raise PolicyError("REASON_REQUIRED", "사유가 필요합니다.")
    return reason.strip()


def validate_rule_or_raise(body: dict) -> dict:
    try:
        return validate_rule(body)
    except RuleInvariantError as exc:
        raise PolicyError("RULE_INVARIANT", str(exc)) from exc
    except ValueError as exc:
        raise PolicyError("RULE_INVALID", str(exc)) from exc


async def _mutate(tenant: str, operation: str, key: str, payload: dict, fn):
    if not key:
        raise PolicyError("IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key가 필요합니다.", 400)
    digest = hashlib.sha256(_json(payload).encode()).hexdigest()
    try:
        return await write_tx(tenant, lambda tx: get_or_create_in_tx(tx, tenant, operation, key, digest, fn))
    except IdempotencyConflict as exc:
        raise PolicyError("IDEMPOTENCY_CONFLICT", str(exc), 409) from exc


async def decide_candidate(tenant: str, actor: str, candidate_id: str, action: str, scope: dict | None, reason: str, key: str, acknowledge_insufficient: bool = False):
    reason = _reason(reason)
    if action not in {"approve", "approve_with_scope_change", "reject"}:
        raise PolicyError("INVALID_ACTION", "잘못된 결정입니다.")
    if action == "approve_with_scope_change" and scope is None:
        raise PolicyError("SCOPE_REQUIRED", "수정 범위가 필요합니다.")
    if scope is not None:
        # Scope is validated using the same deterministic grammar as a rule.
        try:
            validate_rule({"schema": "rule-v1", "rule_id": "R-CHECK-00", "version": 1, "effect": "rule", "target": "ai_need", "scope": scope, "action": {"set": "혼합"}})
        except ValueError as exc:
            raise PolicyError("SCOPE_INVALID", str(exc)) from exc

    async def op(tx):
        row = await (await tx.run("MATCH (c:RuleCandidate {tenant_id:$tenant,id:$id}) SET c._lock=randomUUID() RETURN c.status AS status,c.proposed_body AS proposed_body", tenant=tenant, id=candidate_id)).single()
        if not row:
            raise PolicyError("CANDIDATE_NOT_FOUND", "후보를 찾을 수 없습니다.", 404)
        if row["status"] == "rejected":
            raise PolicyError("CANDIDATE_REJECTED", "기각된 후보입니다.", 409)
        insufficient = row["status"] == "자료 부족"
        if insufficient and action != "reject" and (not acknowledge_insufficient or len(reason) < 10):
            raise PolicyError("INSUFFICIENT_ACK_REQUIRED", "자료 부족 승인에는 확인과 10자 이상의 사유가 필요합니다.")
        existing = await (await tx.run("MATCH (d:RuleDecision {tenant_id:$tenant})-[:DECIDES]->(c:RuleCandidate {tenant_id:$tenant,id:$id}) RETURN d.id AS id LIMIT 1", tenant=tenant, id=candidate_id)).single()
        if existing:
            raise PolicyError("ALREADY_DECIDED", "이미 결정된 후보입니다.", 409)
        confirmed = scope if scope is not None else json.loads(row["proposed_body"] or '{}').get("scope", {"all": []})
        if action != "reject":
            proposed = json.loads(row["proposed_body"] or '{}')
            validate_rule_or_raise({**proposed, "scope": confirmed})
        decision_id = new_id("rule_decision")
        await (await tx.run("MATCH (c:RuleCandidate {tenant_id:$tenant,id:$candidate}) CREATE (d:RuleDecision {id:$id,tenant_id:$tenant,action:$action,decided_by:$actor,reason:$reason,confirmed_scope:$scope,insufficient_approved:$insufficient,acknowledge_insufficient:$ack,decided_at:datetime()})-[:DECIDES]->(c) SET c.status=$status", tenant=tenant, candidate=candidate_id, id=decision_id, action=action, actor=actor, reason=reason, scope=_json(confirmed), insufficient=insufficient and action != "reject", ack=acknowledge_insufficient, status="rejected" if action == "reject" else "approved")).consume()
        await append_audit_in_tx(tx, tenant, actor, "rule.decision", "RuleCandidate", candidate_id, {"status": row["status"]}, {"action": action, "decision_id": decision_id}, reason)
        await append_event_in_tx(tx, tenant, "rule.decision", {"candidate_id": candidate_id, "decision_id": decision_id, "action": action})
        return {"decision_id": decision_id, "candidate_id": candidate_id, "action": action, "confirmed_scope": confirmed, "insufficient_approved": insufficient and action != "reject", "insufficient_approval_label": INSUFFICIENT_APPROVAL_LABEL if insufficient and action != "reject" else None}
    return await _mutate(tenant, "rule.decision", key, {"candidate": candidate_id, "action": action, "scope": scope, "reason": reason, "acknowledge_insufficient": acknowledge_insufficient}, op)


async def create_version(tenant: str, actor: str, rule_id: str, decision_id: str, body: dict, reason: str, key: str, acknowledge_insufficient: bool = False):
    reason = _reason(reason)
    if not RULE_ID.fullmatch(rule_id):
        raise PolicyError("RULE_ID_INVALID", "규칙 ID 형식이 잘못되었습니다.")
    async def op(tx):
        decision = await (await tx.run("MATCH (d:RuleDecision {tenant_id:$tenant,id:$decision})-[:DECIDES]->(c:RuleCandidate {tenant_id:$tenant}) RETURN d.action AS action,d.confirmed_scope AS scope,d.insufficient_approved AS insufficient,c.id AS candidate,c.proposed_body AS proposed_body", tenant=tenant, decision=decision_id)).single()
        if not decision:
            raise PolicyError("DECISION_NOT_FOUND", "승인 결정을 찾을 수 없습니다.", 404)
        if decision["action"] == "reject":
            raise PolicyError("CANDIDATE_REJECTED", "기각된 후보에서 규칙을 만들 수 없습니다.", 409)
        if decision["insufficient"] and (not acknowledge_insufficient or len(reason) < 10):
            raise PolicyError("INSUFFICIENT_ACK_REQUIRED", "자료 부족 규칙 버전 생성에는 확인과 10자 이상의 사유가 필요합니다.")
        row = await (await tx.run("MERGE (s:RuleSeries {tenant_id:$tenant,rule_id:$rule_id}) ON CREATE SET s.next_version=1 SET s._lock=randomUUID() RETURN s.next_version AS version", tenant=tenant, rule_id=rule_id)).single(strict=True)
        version = row["version"]
        proposed = json.loads(decision["proposed_body"] or '{}')
        if body and any(body.get(k) != proposed.get(k) for k in ("effect", "target", "action") if k in body):
            raise PolicyError("CANDIDATE_MISMATCH", "승인된 후보의 규칙 본문과 다릅니다.")
        complete = {**proposed, "schema": "rule-v1", "rule_id": rule_id, "version": version, "candidate_id": decision["candidate"], "decision_id": decision_id, "scope": json.loads(decision["scope"])}
        config_rule = {k: complete.get(k) for k in RULE_REFERENCE_FIELDS}
        _, errors = validate_config({**DEFAULT_CONFIG, "rules": [config_rule]})
        if errors:
            raise PolicyError(errors[0]["code"], errors[0]["reason"])
        await (await tx.run("MATCH (s:RuleSeries {tenant_id:$tenant,rule_id:$rule_id}) SET s.next_version=$next WITH s MATCH (d:RuleDecision {tenant_id:$tenant,id:$decision}) CREATE (r:RuleVersion {id:$id,tenant_id:$tenant,rule_id:$rule_id,version:$version,body:$body,status:'validating',created_at:datetime()})-[:DERIVED_FROM]->(d)", tenant=tenant, rule_id=rule_id, next=version+1, decision=decision_id, id=f"{rule_id}@{version}", version=version, body=_json(complete))).consume()
        await append_audit_in_tx(tx, tenant, actor, "rule.version_created", "RuleVersion", f"{rule_id}@{version}", None, {"status": "validating"}, reason)
        await append_event_in_tx(tx, tenant, "rule.version_created", {"rule_id": rule_id, "version": version})
        return {"rule_id": rule_id, "version": version, "status": "validating", "body": complete, "insufficient_approved": bool(decision["insufficient"]), "insufficient_approval_label": INSUFFICIENT_APPROVAL_LABEL if decision["insufficient"] else None}
    return await _mutate(tenant, "rule.version_created", key, {"rule_id": rule_id, "decision_id": decision_id, "body": body, "reason": reason, "acknowledge_insufficient": acknowledge_insufficient}, op)


async def mark_validated(tenant: str, actor: str, rule_id: str, version: int, validation_id: str, reason: str, key: str):
    reason = _reason(reason)
    async def op(tx):
        row = await (await tx.run("MATCH (r:RuleVersion {tenant_id:$tenant,id:$id}) SET r._lock=randomUUID() RETURN r.status AS status", tenant=tenant, id=f"{rule_id}@{version}")).single()
        if not row:
            raise PolicyError("RULE_NOT_FOUND", "규칙 버전을 찾을 수 없습니다.", 404)
        if row["status"] != "validating":
            raise PolicyError("INVALID_TRANSITION", "검증 중 상태가 아닙니다.", 409)
        validation = await (await tx.run("MATCH (v:ValidationRun {tenant_id:$tenant,id:$id})-[:VALIDATES]->(r:RuleVersion {tenant_id:$tenant,id:$rule}) RETURN v.status AS status,v.side_effects AS side_effects", tenant=tenant, id=validation_id, rule=f"{rule_id}@{version}")).single()
        if not validation or validation["status"] != "completed" or validation["side_effects"] != 0:
            raise PolicyError("VALIDATION_INCOMPLETE", "부작용 0건인 완료 검증이 필요합니다.", 409)
        await (await tx.run("MATCH (r:RuleVersion {tenant_id:$tenant,id:$id}) SET r.status='validated',r.validation_id=$validation", tenant=tenant, id=f"{rule_id}@{version}", validation=validation_id)).consume()
        await append_audit_in_tx(tx, tenant, actor, "rule.validated", "RuleVersion", f"{rule_id}@{version}", {"status": "validating"}, {"status": "validated", "validation_id": validation_id}, reason)
        await append_event_in_tx(tx, tenant, "rule.validated", {"rule_id": rule_id, "version": version, "validation_id": validation_id})
        return {"rule_id": rule_id, "version": version, "status": "validated"}
    return await _mutate(tenant, "rule.validated", key, {"rule_id": rule_id, "version": version, "validation_id": validation_id, "reason": reason}, op)




async def change_publication(tenant: str, actor: str, rule_id: str, operation: str, version: int | None, expected: int, reason: str, key: str):
    reason = _reason(reason)
    async def op(tx):
        reference = None
        if operation in {"publish", "revert"}:
            row = await (await tx.run("MATCH (r:RuleVersion {tenant_id:$tenant,id:$id}) SET r._lock=randomUUID() RETURN r.status AS status,r.body AS body", tenant=tenant, id=f"{rule_id}@{version}")).single()
            if not row:
                raise PolicyError("RULE_NOT_FOUND", "규칙 버전을 찾을 수 없습니다.", 404)
            if operation == "publish" and row["status"] != "validated" or operation == "revert" and row["status"] not in {"published", "stopped", "reverted"}:
                raise PolicyError("INVALID_TRANSITION", "게시 가능한 검증 상태가 아닙니다.", 409)
            body = json.loads(row["body"])
            validate_rule_or_raise(body)
            reference = {k: body.get(k) for k in RULE_REFERENCE_FIELDS}
        else:
            active = await (await tx.run("MATCH (c:ConfigVersion {tenant_id:$tenant,status:'active'}) RETURN c.config_json AS config LIMIT 1", tenant=tenant)).single()
            if not active or not any(r["rule_id"] == rule_id for r in json.loads(active["config"]).get("rules", [])):
                raise PolicyError("RULE_NOT_ACTIVE", "활성 규칙이 아닙니다.", 409)
        result = await publish_config_in_tx(tx, tenant, actor, None, reason, expected, event_kind=f"rule.{operation}", extra_props={"rule_id": rule_id, "reference": reference})
        if operation == "stop":
            await (await tx.run("MATCH (r:RuleVersion {tenant_id:$tenant,rule_id:$rule_id,status:'published'}) SET r.status='stopped'", tenant=tenant, rule_id=rule_id)).consume()
        if operation == "revert":
            await (await tx.run("MATCH (r:RuleVersion {tenant_id:$tenant,rule_id:$rule_id,status:'published'}) WHERE r.version <> $version SET r.status='reverted'", tenant=tenant, rule_id=rule_id, version=version)).consume()
        return result
    return await _mutate(tenant, f"rule.{operation}", key, {"rule_id": rule_id, "version": version, "expected": expected, "reason": reason}, op)


async def list_rules(tenant: str):
    async def op(tx):
        return await (await tx.run("MATCH (r:RuleVersion {tenant_id:$tenant}) RETURN r.rule_id AS rule_id,max(r.version) AS latest_version,count(r) AS version_count ORDER BY rule_id", tenant=tenant)).data()
    return await read_tx(tenant, op)


async def rule_detail(tenant: str, rule_id: str):
    async def op(tx):
        rows = await (await tx.run("MATCH (r:RuleVersion {tenant_id:$tenant,rule_id:$rule_id}) OPTIONAL MATCH (r)-[:DERIVED_FROM]->(d:RuleDecision {tenant_id:$tenant}) OPTIONAL MATCH (r)-[:PUBLISHED_IN]->(c:ConfigVersion {tenant_id:$tenant}) OPTIONAL MATCH (s:RunStep {tenant_id:$tenant})-[a:APPLIED]->(r) RETURN r.version AS version,r.status AS status,r.body AS body,d.insufficient_approved AS insufficient_approved,collect(DISTINCT c.version) AS config_versions,count(DISTINCT a) AS application_count ORDER BY version", tenant=tenant, rule_id=rule_id)).data()
        return [{**row, "body": json.loads(row["body"]), "insufficient_approved": bool(row["insufficient_approved"]), "insufficient_approval_label": INSUFFICIENT_APPROVAL_LABEL if row["insufficient_approved"] else None} for row in rows]
    versions = await read_tx(tenant, op)
    return {"rule_id": rule_id, "versions": versions} if versions else None
