"""Rule administrator API."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from jevtriage.auth.core import Principal, enforce_csrf, require_roles
from jevtriage.learning.rule_access import readable_rule
from jevtriage.learning.rules import (
    change_publication,
    create_version,
    decide_candidate,
    list_rules,
    mark_validated,
    rule_detail,
)
from jevtriage.policy.service import PolicyError

router = APIRouter(prefix="/api/learning", tags=["learning"])
ADMIN = Depends(require_roles("rule_admin"))
READ = Depends(require_roles("reviewer", "rule_admin", "operator"))
CSRF = Depends(enforce_csrf)


class DecisionBody(BaseModel):
    action: str
    scope: dict[str, Any] | None = None
    reason: str = Field(min_length=1)
    acknowledge_insufficient: bool = False


class VersionBody(BaseModel):
    decision_id: str
    body: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(min_length=1)
    acknowledge_insufficient: bool = False


class ValidateBody(BaseModel):
    validation_id: str
    reason: str = Field(min_length=1)


class ChangeBody(BaseModel):
    expected_active_config_version: int = Field(ge=0)
    reason: str = Field(min_length=1)


class RevertBody(ChangeBody):
    to_version: int = Field(ge=1)


def _key(request: Request) -> str:
    value = request.headers.get("Idempotency-Key")
    if not value:
        raise HTTPException(400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED"})
    return value


def _error(exc: PolicyError):
    raise HTTPException(exc.status_code, detail={"code": exc.code, "reason": exc.reason}) from exc


@router.post("/candidates/{candidate_id}/decision", dependencies=[CSRF])
async def decision(candidate_id: str, body: DecisionBody, request: Request, principal: Principal = ADMIN):
    try:
        return await decide_candidate(principal.tenant_id, principal.user_id, candidate_id, body.action, body.scope, body.reason, _key(request), body.acknowledge_insufficient)
    except PolicyError as exc:
        _error(exc)


@router.post("/rules/{rule_id}/versions", dependencies=[CSRF])
async def version_create(rule_id: str, body: VersionBody, request: Request, principal: Principal = ADMIN):
    try:
        return await create_version(principal.tenant_id, principal.user_id, rule_id, body.decision_id, body.body, body.reason, _key(request), body.acknowledge_insufficient)
    except PolicyError as exc:
        _error(exc)


@router.post("/rules/{rule_id}/versions/{version}/mark-validated", dependencies=[CSRF])
async def validated(rule_id: str, version: int, body: ValidateBody, request: Request, principal: Principal = ADMIN):
    try:
        return await mark_validated(principal.tenant_id, principal.user_id, rule_id, version, body.validation_id, body.reason, _key(request))
    except PolicyError as exc:
        _error(exc)


@router.post("/rules/{rule_id}/versions/{version}/publish", dependencies=[CSRF])
async def publish(rule_id: str, version: int, body: ChangeBody, request: Request, principal: Principal = ADMIN):
    try:
        return await change_publication(principal.tenant_id, principal.user_id, rule_id, "publish", version, body.expected_active_config_version, body.reason, _key(request))
    except PolicyError as exc:
        _error(exc)


@router.post("/rules/{rule_id}/stop", dependencies=[CSRF])
async def stop(rule_id: str, body: ChangeBody, request: Request, principal: Principal = ADMIN):
    try:
        return await change_publication(principal.tenant_id, principal.user_id, rule_id, "stop", None, body.expected_active_config_version, body.reason, _key(request))
    except PolicyError as exc:
        _error(exc)


@router.post("/rules/{rule_id}/revert", dependencies=[CSRF])
async def revert(rule_id: str, body: RevertBody, request: Request, principal: Principal = ADMIN):
    try:
        return await change_publication(principal.tenant_id, principal.user_id, rule_id, "revert", body.to_version, body.expected_active_config_version, body.reason, _key(request))
    except PolicyError as exc:
        _error(exc)


@router.get("/rules")
async def rules(principal: Principal = READ):
    visible = []
    for row in await list_rules(principal.tenant_id):
        detail = readable_rule(principal, await rule_detail(principal.tenant_id, row["rule_id"]))
        if detail:
            versions = detail["versions"]
            visible.append({**row, "latest_version": max(v["version"] for v in versions),
                            "version_count": len(versions)})
    return {"rules": visible}


@router.get("/rules/{rule_id}")
async def detail(rule_id: str, principal: Principal = READ):
    result = await rule_detail(principal.tenant_id, rule_id)
    result = readable_rule(principal, result) if result else None
    if result is None:
        raise HTTPException(404, detail={"code": "RULE_NOT_FOUND"})
    return result
