"""Account administration API (admin role only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ildongi.auth.core import Principal, require_roles
from ildongi.auth.users import UserAdminError, create_user, list_users, update_user, user_detail
from ildongi.domain.api_types import Int64

router = APIRouter(prefix="/api/admin/users", tags=["admin"])
ADMIN = Depends(require_roles("admin"))


class UserCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Int64 = Field(ge=0)
    roles: list[str] = Field(max_length=20)
    org_ids: list[str] = Field(max_length=50)
    disabled: bool
    can_read_source: bool
    reason: str = Field(max_length=1000)


class NewUserCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=254)
    display_name: str | None = Field(default=None, max_length=80)
    roles: list[str] = Field(max_length=20)
    org_ids: list[str] = Field(max_length=50)
    can_read_source: bool = False
    reason: str = Field(max_length=1000)


def _fail(exc: UserAdminError) -> HTTPException:
    return HTTPException(exc.status_code, {"message": str(exc)})


@router.get("")
async def users(principal: Principal = ADMIN):
    try:
        return await list_users(principal)
    except UserAdminError as exc:
        raise _fail(exc) from exc


@router.post("", status_code=201)
async def issue(command: NewUserCommand, principal: Principal = ADMIN):
    try:
        return await create_user(principal, command.model_dump())
    except UserAdminError as exc:
        raise _fail(exc) from exc


@router.get("/{user_id}")
async def user(user_id: str, principal: Principal = ADMIN):
    try:
        return await user_detail(principal, user_id)
    except UserAdminError as exc:
        raise _fail(exc) from exc


@router.post("/{user_id}")
async def change(user_id: str, command: UserCommand, principal: Principal = ADMIN):
    try:
        return await update_user(principal, user_id, command.model_dump())
    except UserAdminError as exc:
        raise _fail(exc) from exc
