"""Dynamic policy validation, versioning, publication and rollback."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from pydantic_core import PydanticCustomError

from ildongi.db.audit import append_audit_in_tx
from ildongi.db.events import append_event_in_tx
from ildongi.db.idempotency import IdempotencyConflict, get_or_create_in_tx
from ildongi.db.tx import read_tx, write_tx
from ildongi.domain.masking import CATEGORIES
from ildongi.domain.rules import RuleInvariantError, validate_rule

POLICY_SCHEMA_VERSION = "policy-schema-v1"
LIMIT_MAXIMA = {"text_chars": 20000, "attachments": 5, "file_bytes": 10485760, "total_bytes": 26214400, "pdf_pages": 50}
RULE_REFERENCE_FIELDS = ("rule_id", "version", "effect", "target", "scope", "action", "context_text", "candidate_id", "decision_id")


class RuleReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rule_id: str
    version: int = Field(ge=1)
    effect: str
    target: str
    scope: dict[str, Any] = Field(default_factory=dict)
    action: dict[str, Any] = Field(default_factory=dict)
    context_text: str | None = None
    candidate_id: str | None = None
    decision_id: str | None = None

    @model_validator(mode="after")
    def valid_effect(self):
        try:
            validate_rule({"schema": "rule-v1", **self.model_dump(), "rule_id": self.rule_id, "version": self.version})
        except RuleInvariantError as exc:
            raise PydanticCustomError("rule_invariant", "{reason}", {"reason": str(exc)}) from exc
        return self


class LearningConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min_support: int = Field(default=3, ge=2)
    min_effect_sample: int = Field(default=20, ge=5)
    shadow_max_calls: int = Field(default=20, ge=0, le=200)
    effect_window_days: int = Field(default=7, ge=1, le=90)


class MaskingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    categories: list[str] = Field(default_factory=lambda: [
        "registration", "business", "card", "email", "phone", "account", "ip",
        "url_query", "api_key",
    ])

    @model_validator(mode="after")
    def valid_categories(self):
        if len(set(self.categories)) != len(self.categories) or set(self.categories) - set(CATEGORIES):
            raise ValueError("unknown or duplicate masking category")
        return self


class RetentionSettings(BaseModel):
    """Development defaults only; operators must confirm production periods."""
    model_config = ConfigDict(extra="forbid")
    event_days: int = Field(default=90, ge=1, le=3650)
    idempotency_days: int = Field(default=30, ge=1, le=3650)
    session_grace_days: int = Field(default=7, ge=0, le=3650)
    login_attempt_window_seconds: int = Field(default=900, ge=1, le=2592000)
    journal_days: int = Field(default=90, ge=1, le=3650)
    metrics_days: int = Field(default=90, ge=1, le=3650)
    batch_size: int = Field(default=500, ge=1, le=10000)


class LlmFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: bool = False
    task_description: bool = False
    questions: bool = False
    rule_explanation: bool = False


class LlmConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["anthropic", "openai", "google", "chatgpt"] | None = None
    model: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._:/-]{1,100}$")
    features: LlmFeatures = Field(default_factory=LlmFeatures)
    timeout_seconds: float = Field(default=15, ge=1, le=60)
    step_budget_seconds: float = Field(default=20, ge=1, le=90)
    max_output_tokens: int = Field(default=2000, ge=256, le=8000)

    @model_validator(mode="after")
    def model_required(self):
        if self.provider and not self.model:
            raise ValueError("llm.model is required when llm.provider is set")
        return self


class PolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = POLICY_SCHEMA_VERSION
    auto_assign: bool = False
    choice_confidence_thresholds: dict[str, float] = Field(default_factory=lambda: {"ai_need": .8, "feasibility": .8, "urgency": .8, "lead_org": .8})
    noul_probability_thresholds: dict[str, float] = Field(default_factory=lambda: {"evidence": .6, "catalog": .6})
    noul_uncertain_band: list[float] = Field(default_factory=lambda: [.35, .65])
    risk_clear_max: float = .2
    reviewer_groups: dict[str, list[str]] = Field(default_factory=dict)
    limits: dict[str, int] = Field(default_factory=lambda: {"text_chars": 20000, "attachments": 5, "file_bytes": 10485760, "total_bytes": 26214400, "pdf_pages": 50})
    evidence_noul_threshold: float = .6
    catalog_noul_threshold: float = .6
    feature_flags: dict[str, bool] = Field(default_factory=dict)
    rules: list[RuleReference] = Field(default_factory=list)
    learning: LearningConfig = Field(default_factory=LearningConfig)
    masking: MaskingConfig = Field(default_factory=MaskingConfig)
    llm: LlmConfig = Field(default_factory=LlmConfig)
    retention: RetentionSettings = Field(default_factory=RetentionSettings)

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.schema_version != POLICY_SCHEMA_VERSION:
            raise ValueError("unsupported schema_version")
        for value in [*self.choice_confidence_thresholds.values(), *self.noul_probability_thresholds.values(), self.risk_clear_max, self.evidence_noul_threshold, self.catalog_noul_threshold]:
            if not 0 <= value <= 1:
                raise ValueError("thresholds must be between 0 and 1")
        if len(self.noul_uncertain_band) != 2 or not 0 <= self.noul_uncertain_band[0] < self.noul_uncertain_band[1] <= 1:
            raise ValueError("noul_uncertain_band must satisfy 0 <= low < high <= 1")
        # PRD 7: text 20k chars, 5 attachments, 10 MiB/file, 25 MiB total, 50 PDF pages.
        for key, maximum in LIMIT_MAXIMA.items():
            if key in self.limits and not 0 <= self.limits[key] <= maximum:
                raise ValueError(f"limits.{key} exceeds supported maximum {maximum}")
        return self


DEFAULT_CONFIG = PolicyConfig().model_dump(mode="json")


async def bootstrap_policy(tenant: str) -> None:
    """Create conservative version 1 if a tenant has no policy yet."""
    async def op(tx):
        await (await tx.run("MERGE (p:Policy {tenant_id:$tenant}) ON CREATE SET p.next_version=1, p.active_version=0 SET p._lock=randomUUID() RETURN p.active_version AS active", tenant=tenant)).consume()
        exists = await (await tx.run("MATCH (c:ConfigVersion {tenant_id:$tenant}) RETURN count(c) AS n", tenant=tenant)).single(strict=True)
        if exists["n"]:
            return
        await (await tx.run("MATCH (p:Policy {tenant_id:$tenant}) SET p.next_version=2, p.active_version=1 CREATE (:ConfigVersion {id:$id, tenant_id:$tenant, version:1, status:'active', created_by:'system:bootstrap', reason:'보수적 초기 정책', config_json:$config, diff_json:'{}', created_at:datetime()})", tenant=tenant, id=f"cfg_{tenant}_1", config=json.dumps(DEFAULT_CONFIG, ensure_ascii=False, separators=(",", ":")))).consume()
    await write_tx(tenant, op)


class PolicyError(Exception):
    def __init__(self, code: str, reason: str, status_code: int = 422):
        self.code, self.reason, self.status_code = code, reason, status_code
        super().__init__(reason)


def validate_invariants(config: dict[str, Any] | PolicyConfig) -> list[dict[str, str]]:
    model = config if isinstance(config, PolicyConfig) else PolicyConfig.model_validate(config)
    issues: list[dict[str, str]] = []
    if model.llm.provider and not model.masking.enabled:
        issues.append({"code": "LLM_REQUIRES_MASKING", "reason": "글쓰기 보조는 마스킹을 켠 상태에서만 사용할 수 있습니다."})
    if model.risk_clear_max > .5:
        issues.append({"code": "RISK_BAND_TOO_PERMISSIVE", "reason": "risk_clear_max는 0.5를 초과할 수 없습니다."})
    return issues


def validate_config(raw: dict[str, Any], *, allow_rules: bool = True) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    try:
        config = PolicyConfig.model_validate(raw)
    except ValidationError as exc:
        return None, [{"code": "RULE_INVARIANT" if e["type"] == "rule_invariant" else "SCHEMA_INVALID", "reason": e["msg"]} for e in exc.errors()]
    issues = validate_invariants(config)
    if not allow_rules and config.rules:
        issues.append({"code": "RULE_ADMIN_REQUIRED", "reason": "rules 변경은 rule_admin 전용 경로에서만 허용됩니다."})
    return config.model_dump(mode="json"), issues


async def get_active_snapshot(tenant: str) -> tuple[int, dict[str, Any]]:
    async def op(tx):
        row = await (await tx.run("MATCH (c:ConfigVersion {tenant_id:$tenant, status:'active'}) RETURN c.version AS version, c.config_json AS config_json ORDER BY c.version DESC LIMIT 1", tenant=tenant)).single()
        if row:
            return row["version"], json.loads(row["config_json"])
        return 0, DEFAULT_CONFIG.copy()
    return await read_tx(tenant, op)


async def validate_for_tenant(raw: dict[str, Any], tenant: str):
    config, errors = validate_config(raw)
    if config is not None:
        _, active = await get_active_snapshot(tenant)
        if config["rules"] != active.get("rules", []):
            errors.append({"code": "RULE_ADMIN_REQUIRED", "reason": "rules 변경은 rule_admin 전용 경로에서만 허용됩니다."})
    return config, errors


async def get_version(tenant: str, version: int) -> dict[str, Any] | None:
    async def op(tx):
        row = await (await tx.run("MATCH (c:ConfigVersion {tenant_id:$tenant, version:$version}) RETURN c.version AS version, c.status AS status, c.config_json AS config_json, c.diff_json AS diff_json, c.created_by AS created_by, c.reason AS reason, toString(c.created_at) AS created_at", tenant=tenant, version=version)).single()
        if not row:
            return None
        return {"version": row["version"], "status": row["status"], "config": json.loads(row["config_json"]), "diff": json.loads(row["diff_json"]), "created_by": row["created_by"], "reason": row["reason"], "created_at": row["created_at"]}
    return await read_tx(tenant, op)


async def list_versions(tenant: str) -> list[dict[str, Any]]:
    async def op(tx):
        rows = await (await tx.run("MATCH (c:ConfigVersion {tenant_id:$tenant}) RETURN c.version AS version, c.status AS status, c.reason AS reason, c.created_by AS created_by, toString(c.created_at) AS created_at ORDER BY c.version DESC", tenant=tenant)).data()
        return [dict(row) for row in rows]
    return await read_tx(tenant, op)


async def publish_config_in_tx(tx, tenant: str, actor: str, config: dict[str, Any] | None,
                               reason: str, expected: int, *, event_kind: str,
                               extra_props: dict[str, Any]):
    rule_id = extra_props.get("rule_id")
    reference = extra_props.get("reference")
    rule_publish = rule_id is not None
    lock = await (await tx.run("MERGE (p:Policy {tenant_id:$tenant}) ON CREATE SET p.next_version=1,p.active_version=0 SET p._lock=randomUUID() RETURN p.active_version AS active,p.next_version AS next", tenant=tenant)).single(strict=True)
    if lock["active"] != expected:
        raise PolicyError("ACTIVE_VERSION_CONFLICT", "활성 Config 버전이 다릅니다." if rule_publish else "expected_active_version이 현재 활성 버전과 다릅니다.", 409)
    prior_row = await (await tx.run("MATCH (c:ConfigVersion {tenant_id:$tenant,version:$version}) RETURN c.config_json AS config", tenant=tenant, version=expected)).single() if expected else None
    if expected and not prior_row:
        raise PolicyError("ACTIVE_VERSION_MISSING", "활성 Config를 찾을 수 없습니다." if rule_publish else "현재 활성 버전을 찾을 수 없습니다.", 409)
    prior = json.loads(prior_row["config"]) if prior_row else DEFAULT_CONFIG
    if not rule_publish:
        if prior.get("rules", []) != config.get("rules", []):
            raise PolicyError("RULE_ADMIN_REQUIRED", "rules 변경은 rule_admin 전용 경로에서만 허용됩니다.")
        diff = {key: {"before": prior.get(key), "after": val} for key, val in config.items() if prior.get(key) != val}
        payload_json = extra_props["payload_json"]
        row = await (await tx.run("MATCH (p:Policy {tenant_id:$tenant}) WITH p, p.next_version AS v SET p.next_version=v+1, p.active_version=v WITH p,v OPTIONAL MATCH (old:ConfigVersion {tenant_id:$tenant,status:'active'}) SET old.status='superseded' CREATE (c:ConfigVersion {id:$id, tenant_id:$tenant, version:v, status:'active', created_by:$actor, reason:$reason, config_json:$config_json, diff_json:$diff_json, created_at:datetime()}) RETURN v", tenant=tenant, id=f"cfg_{tenant}_{expected+1}", actor=actor, reason=reason, config_json=payload_json, diff_json=json.dumps(diff, ensure_ascii=False, separators=(",", ":")))).single(strict=True)
        version = row["v"]
        await append_audit_in_tx(tx, tenant, actor, "policy.publish", "ConfigVersion", str(version), {"version": expected, "config": prior}, {"version": version, "config": config}, reason)
        await append_event_in_tx(tx, tenant, event_kind, {"version": version, "previous_version": expected})
        return {"version": version, "status": "active", "config": config, "diff": diff}
    rules = [r for r in prior.get("rules", []) if r["rule_id"] != rule_id]
    if reference is not None:
        rules.append(reference)
    updated, errors = validate_config({**prior, "rules": rules})
    if errors:
        raise PolicyError(errors[0]["code"], errors[0]["reason"])
    version = lock["next"]
    diff = {"rules": {"before": prior.get("rules", []), "after": rules}}
    await (await tx.run("MATCH (p:Policy {tenant_id:$tenant}) SET p.next_version=$next,p.active_version=$version WITH p OPTIONAL MATCH (old:ConfigVersion {tenant_id:$tenant,status:'active'}) SET old.status='superseded' CREATE (c:ConfigVersion {id:$id,tenant_id:$tenant,version:$version,status:'active',created_by:$actor,reason:$reason,config_json:$config,diff_json:$diff,created_at:datetime()}) RETURN c", tenant=tenant, next=version+1, version=version, id=f"cfg_{tenant}_{version}", actor=actor, reason=reason, config=json.dumps(updated, ensure_ascii=False, sort_keys=True, separators=(",", ":")), diff=json.dumps(diff, ensure_ascii=False, sort_keys=True, separators=(",", ":")))).single(strict=True)
    if reference is not None:
        await (await tx.run("MATCH (r:RuleVersion {tenant_id:$tenant,id:$rule}) MATCH (c:ConfigVersion {tenant_id:$tenant,version:$version}) CREATE (r)-[:PUBLISHED_IN]->(c) SET r.status='published'", tenant=tenant, rule=f"{reference['rule_id']}@{reference['version']}", version=version)).consume()
    await append_audit_in_tx(tx, tenant, actor, event_kind, "ConfigVersion", str(version), {"version": expected, "rules": prior.get("rules", [])}, {"version": version, "rules": rules}, reason)
    await append_event_in_tx(tx, tenant, event_kind, {"rule_id": rule_id, "config_version": version, "previous_version": expected})
    return {"config_version": version, "rules": rules}


async def publish(tenant: str, actor: str, raw: dict[str, Any], reason: str, expected: int, *, idempotency_key: str):
    config, errors = validate_config(raw)
    if errors:
        raise PolicyError(errors[0]["code"], errors[0]["reason"])
    if not reason.strip():
        raise PolicyError("REASON_REQUIRED", "변경 사유가 필요합니다.")
    payload_json = json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    async def op(tx):
        return await publish_config_in_tx(tx, tenant, actor, config, reason.strip(), expected,
                                          event_kind="policy.published", extra_props={"payload_json": payload_json})
    # lock and expected-version check are serialized in the same Neo4j transaction.
    digest = hashlib.sha256((payload_json + reason + str(expected)).encode()).hexdigest()
    try:
        return await write_tx(tenant, lambda tx: get_or_create_in_tx(tx, tenant, "policy.publish", idempotency_key, digest, op))
    except IdempotencyConflict as exc:
        raise PolicyError("IDEMPOTENCY_CONFLICT", str(exc), 409) from exc


async def rollback(tenant: str, actor: str, target: int, reason: str, expected: int, *, idempotency_key: str):
    target_version = await get_version(tenant, target)
    if not target_version:
        raise PolicyError("VERSION_NOT_FOUND", "되돌릴 버전을 찾을 수 없습니다.", 404)
    # Rules are owned by T32; rollback cannot alter them in the general editor path.
    return await publish(tenant, actor, target_version["config"], reason, expected, idempotency_key=idempotency_key)
