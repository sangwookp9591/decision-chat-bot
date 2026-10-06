"""Policy configuration API."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ildongi.auth.core import Principal, enforce_csrf, get_principal, require_roles
from ildongi.domain.api_types import Int64
from ildongi.policy.service import (
    PolicyError,
    get_active_snapshot,
    get_version,
    list_versions,
    publish,
    rollback,
    validate_config,
)

router = APIRouter(prefix="/api/policy", tags=["policy"])


class ValidateBody(BaseModel):
    config: dict[str, Any]


class PublishBody(BaseModel):
    config: dict[str, Any]
    reason: str = Field(min_length=1)
    expected_active_version: Int64 = Field(ge=0)


class RollbackBody(BaseModel):
    target_version: Int64 = Field(ge=1)
    reason: str = Field(min_length=1)
    expected_active_version: Int64 = Field(ge=0)


def _raise(exc: PolicyError):
    raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "reason": exc.reason})


@router.get("/active")
async def active(principal: Principal = Depends(get_principal)):  # noqa: B008
    version, config = await get_active_snapshot(principal.tenant_id)
    return {"version": version, "config": config}


@router.get("/versions")
async def versions(principal: Principal = Depends(get_principal)):  # noqa: B008
    return {"versions": await list_versions(principal.tenant_id)}


@router.get("/versions/{version}")
async def version_detail(version: Int64, principal: Principal = Depends(get_principal)):  # noqa: B008
    result = await get_version(principal.tenant_id, version)
    if result is None:
        raise HTTPException(status_code=404, detail={"code": "VERSION_NOT_FOUND"})
    return result


@router.post("/validate")
async def validate(body: ValidateBody, principal: Principal = Depends(get_principal)):  # noqa: B008
    del principal
    config, errors = validate_config(body.config, allow_rules=False)
    return {"valid": not errors, "config": config, "errors": errors}


@router.post("/publish", dependencies=[Depends(enforce_csrf)])
async def publish_config(body: PublishBody, request: Request, principal: Principal = Depends(require_roles("policy_editor"))):  # noqa: B008
    key = request.headers.get("Idempotency-Key")
    if not key:
        raise HTTPException(status_code=400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED"})
    try:
        return await publish(principal.tenant_id, principal.user_id, body.config, body.reason, body.expected_active_version, idempotency_key=key)
    except PolicyError as exc:
        _raise(exc)


@router.post("/rollback", dependencies=[Depends(enforce_csrf)])
async def rollback_config(body: RollbackBody, request: Request, principal: Principal = Depends(require_roles("policy_editor"))):  # noqa: B008
    if not request.headers.get("Idempotency-Key"):
        raise HTTPException(status_code=400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED"})
    try:
        return await rollback(principal.tenant_id, principal.user_id, body.target_version, body.reason, body.expected_active_version, idempotency_key=request.headers["Idempotency-Key"])
    except PolicyError as exc:
        _raise(exc)
