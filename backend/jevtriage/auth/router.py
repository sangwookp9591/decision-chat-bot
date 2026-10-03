from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from jevtriage.auth.core import (
    LOGIN_FAILURE_LIMIT,
    Principal,
    _token_hash,
    authenticate,
    create_session,
    enforce_csrf,
    get_principal,
    increment_login_attempt,
    login_attempt_count,
    reset_login_attempt,
    session_principal,
)
from jevtriage.config import get_settings
from jevtriage.db.driver import get_driver

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(body: LoginBody, request: Request, response: Response):
    # Resolve the counter namespace before password work for both known and unknown users.
    driver = await get_driver()
    async with driver.session() as session:
        user = await (await session.run(
            "MATCH (u:User {email:$email}) RETURN u.tenant_id AS tenant_id LIMIT 1",
            email=body.email.lower(),
        )).single()
    tenant_id = user["tenant_id"] if user else "unknown"
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
        "jev_session",
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
        "jev_csrf",
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
    token = request.cookies.get("jev_session")
    if token:
        driver = await get_driver()
        async with driver.session() as session:
            await (
                await session.run(
                    "MATCH (s:Session {token_hash:$hash}) DETACH DELETE s",
                    hash=_token_hash(token),
                )
            ).consume()
    response.delete_cookie("jev_session", path="/")
    response.delete_cookie("jev_csrf", path="/")
    return {"ok": True}


@router.get("/me")
async def me(request: Request, principal: Principal = Depends(get_principal)):  # noqa: B008
    csrf_token = getattr(request.state, "csrf_token", None)
    driver = await get_driver()
    async with driver.session() as session:
        record = await (
            await session.run(
                "MATCH (u:User {id:$user_id,tenant_id:$tenant_id}) RETURN u.display_name AS display_name",
                user_id=principal.user_id,
                tenant_id=principal.tenant_id,
            )
        ).single()
    return {
        "tenant_id": principal.tenant_id,
        "user_id": principal.user_id,
        "display_name": record["display_name"] if record else None,
        "mode": get_settings().jev_mode,
        "org_ids": principal.org_ids,
        "roles": sorted(principal.roles),
        "can_read_source": principal.can_read_source,
        "csrf_token": csrf_token,
    }
