"""Decision case list and lifecycle API."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from ildongi.auth.core import Principal, require_roles
from ildongi.domain.api_types import Int64
from ildongi.review.cases import FIELDS, STATUSES, CaseError, change_case, list_cases

router = APIRouter(prefix="/api/cases", tags=["cases"])
READ = Depends(require_roles("reviewer", "rule_admin", "operator"))


class CaseCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Int64 = Field(ge=1)
    conditions: list[str] | None = None
    exceptions: list[str] | None = None
    outcome: Literal["held", "failed"] | None = None
    note: str | None = Field(default=None, max_length=1000)
    reason: str | None = Field(default=None, max_length=1000)
    to_version: Int64 | None = Field(default=None, ge=1)


@router.get("")
async def cases(status: str | None = Query(None), field: str | None = Query(None),
                principal: Principal = READ):
    if status is not None and status not in STATUSES or field is not None and field not in FIELDS:
        raise HTTPException(422, "Invalid filter")
    return {"cases": await list_cases(principal, status, field)}


@router.post("/{case_id}/{action}")
async def case_action(case_id: str, action: Literal["confirm", "outcome", "retire", "revert"],
                      command: CaseCommand, principal: Principal = READ):
    try:
        return await change_case(principal, case_id, action, command.model_dump(exclude_none=True))
    except CaseError as exc:
        raise HTTPException(exc.status_code, {"message": str(exc)}) from exc
