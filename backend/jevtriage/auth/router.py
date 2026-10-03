from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from jevtriage.auth.core import (
    Principal,
    authenticate,
    create_session,
    enforce_csrf,
    get_principal,
    increment_login_attempt,
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
    account = await authenticate(body.email.lower(), body.password)
    if not account:
        # Unknown accounts share a reserved tenant namespace while known accounts
        # are counted against their tenant/email uniqueness key.
        driver = await get_driver()
        async with driver.session() as session:
            user = await (await session.run(
                "MATCH (u:User {email:$email}) RETURN u.tenant_id AS tenant_id LIMIT 1",
                email=body.email.lower(),
            )).single()
        count = await increment_login_attempt(user["tenant_id"] if user else "unknown", body.email)
        if count > 10:
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
    resolved = await session_principal(token)
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
                    hash=__import__("hashlib").sha256(token.encode()).hexdigest(),
                )
            ).consume()
    response.delete_cookie("jev_session", path="/")
    response.delete_cookie("jev_csrf", path="/")
    return {"ok": True}


@router.get("/me")
async def me(request: Request, principal: Principal = Depends(get_principal)):  # noqa: B008
    resolved = await session_principal(request.cookies.get("jev_session"))
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
        "csrf_token": resolved[1] if resolved else None,
    }
