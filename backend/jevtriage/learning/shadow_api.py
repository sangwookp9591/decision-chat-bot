from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from jevtriage.auth.core import Principal, require_roles
from jevtriage.domain.serialize import json_value
from jevtriage.learning.shadow import rule_validations, validate_rules, validation_detail

router = APIRouter(prefix="/api/learning/rules", tags=["learning"])
validation_router = APIRouter(prefix="/api/learning/validations", tags=["learning"])


class Body(BaseModel):
    from_: datetime = Field(alias="from")
    to: datetime
    scope_filter: str | None = None
    max_calls: int | None = None
    model_config = {"populate_by_name": True}


@router.post("/{rule_id}/versions/{version}/validate")
async def validate(rule_id: str, version: int, body: Body,
                   principal: Principal = Depends(require_roles("rule_admin"))):  # noqa: B008
    try:
        result = await validate_rules(principal.tenant_id, principal.user_id, rule_id, version,
                                      body.from_, body.to, body.scope_filter, body.max_calls)
        return json_value(result)
    except LookupError:
        raise HTTPException(404, detail={"code": "RULE_VERSION_NOT_FOUND"})
    except ValueError as exc:
        raise HTTPException(422, detail={"code": "INVALID_RANGE", "reason": str(exc)})

@validation_router.get("/{validation_id}")
async def get_validation(validation_id: str,
                         principal: Principal = Depends(require_roles("rule_admin", "operator", "reviewer"))):  # noqa: B008
    result = await validation_detail(principal.tenant_id, validation_id)
    if result is None:
        raise HTTPException(404, detail="Validation not found")
    return result

@router.get("/{rule_id}/versions/{version}/validations")
async def list_validations(rule_id: str, version: int,
                           principal: Principal = Depends(require_roles("rule_admin", "operator", "reviewer"))):  # noqa: B008
    return {"validations": await rule_validations(principal.tenant_id, rule_id, version)}
