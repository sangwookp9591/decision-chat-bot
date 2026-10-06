from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from ildongi.auth.core import (
    LOGIN_FAILURE_LIMIT,
    Principal,
    authenticate,
    create_session,
    enforce_csrf,
    get_principal,
    increment_login_attempt,
    login_attempt_count,
    login_tenant,
    principal_display_name,
    reset_login_attempt,
    revoke_session,
    session_principal,
)
from ildongi.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(body: LoginBody, request: Request, response: Response):
    # Resolve the counter namespace before password work for both known and unknown users.
    tenant_id = await login_tenant(body.email)
    if await login_attempt_count(tenant_id, body.email) >= LOGIN_FAILURE_LIMIT:
        raise HTTPException(status_code=429, detail="Login temporarily unavailable")
    account = await authenticate(body.email.lower(), body.password)
    if not account:
        count = await increment_login_attempt(tenant_id, body.email)
        if count > LOGIN_FAILURE_LIMIT:
            raise HTTPException(status_code=429, detail="Login temporarily unavailable")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await reset_login_attempt(account["tenant_id"], body.email)
    token = await create_session(account["tenant_id"], account["user_id"])
    response.set_cookie(
        "ildongi_session",
        token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=43200,
        path="/",
    )
    csrf_token = getattr(request.state, "csrf_token", None)
    resolved = (None, csrf_token) if csrf_token else await session_principal(token)
    response.set_cookie(
        "ildongi_csrf",
        resolved[1],
        httponly=False,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=43200,
        path="/",
    )
    return {"ok": True}


@router.post("/logout", dependencies=[Depends(enforce_csrf)])
async def logout(request: Request, response: Response):
    token = request.cookies.get("ildongi_session")
    if token:
        await revoke_session(token)
    response.delete_cookie("ildongi_session", path="/")
    response.delete_cookie("ildongi_csrf", path="/")
    return {"ok": True}


@router.get("/me")
async def me(request: Request, principal: Principal = Depends(get_principal)):  # noqa: B008
    csrf_token = getattr(request.state, "csrf_token", None)
    return {
        "tenant_id": principal.tenant_id,
        "user_id": principal.user_id,
        "display_name": await principal_display_name(principal),
        "mode": get_settings().ai_mode,
        "org_ids": principal.org_ids,
        "roles": sorted(principal.roles),
        "can_read_source": principal.can_read_source,
        "csrf_token": csrf_token,
    }
