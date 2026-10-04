"""Tenant scoped authentication, authorization, and persisted sessions."""

import asyncio
import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyCookie

from jevtriage.auth.policy import can
from jevtriage.auth.policy import scope_filter_cypher as policy_scope_filter_cypher
from jevtriage.auth.store import delete_session, display_name, tenant_for_email
from jevtriage.auth.types import Principal
from jevtriage.db.tx import cross_tenant_tx, read_tx, write_tx

_hasher = PasswordHasher()
_DUMMY_PASSWORD_HASH = "$argon2id$v=19$m=65536,t=3,p=4$LkzPCpGAGkB5SROqN9l+6A$bVKong4Ml+CFR/rV6mhd+DaNvDW79BaFRYXeEHZkVOE"
_cookie = APIKeyCookie(name="jev_session", auto_error=False)
SESSION_HOURS = 12
LOGIN_FAILURE_LIMIT = int(os.getenv("LOGIN_FAILURE_LIMIT", "10"))
LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", "900"))


async def login_attempt_count(tenant_id: str, email: str) -> int:
    """Read the live failure count; expired windows read as zero."""
    async def query(tx):
        row = await (await tx.run(
            "MATCH (l:LoginAttempt {tenant_id:$tenant,email:$email}) "
            "RETURN CASE WHEN l.window_start + duration({seconds:$window}) <= datetime() "
            "THEN 0 ELSE l.count END AS count",
            tenant=tenant_id, email=email.lower(), window=LOGIN_WINDOW_SECONDS,
        )).single()
        return row["count"] if row else 0
    count = await read_tx(tenant_id, query)
    return count


async def increment_login_attempt(tenant_id: str, email: str) -> int:
    """Atomically create/increment the tenant/email failure counter."""
    async def query(tx):
        row = await (await tx.run(
            "MERGE (l:LoginAttempt {tenant_id:$tenant,email:$email}) "
            "ON CREATE SET l.count=0,l.window_start=datetime() "
            "SET l._lock=randomUUID() "
            "WITH l, datetime() AS now "
            "SET l.count=CASE WHEN l.window_start + duration({seconds:$window}) <= now "
            "THEN 1 ELSE l.count+1 END, "
            "l.window_start=CASE WHEN l.window_start + duration({seconds:$window}) <= now "
            "THEN now ELSE l.window_start END "
            "RETURN l.count AS count",
            tenant=tenant_id, email=email.lower(), window=LOGIN_WINDOW_SECONDS,
        )).single(strict=True)
        return row["count"]
    return await write_tx(tenant_id, query)


async def reset_login_attempt(tenant_id: str, email: str) -> None:
    async def query(tx):
        await (await tx.run(
            "MATCH (l:LoginAttempt {tenant_id:$tenant,email:$email}) SET l.count=0",
            tenant=tenant_id, email=email.lower(),
        )).consume()
    await write_tx(tenant_id, query)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def login_tenant(email: str) -> str:
    return await tenant_for_email(email)


async def revoke_session(token: str) -> None:
    await delete_session(_token_hash(token))


async def principal_display_name(principal: Principal) -> str | None:
    return await display_name(principal.tenant_id, principal.user_id)


async def authenticate(email: str, password: str) -> dict[str, Any] | None:
    async def query(tx):
        result = await tx.run(
            "MATCH (u:User {email: $email}) WHERE u.disabled = false "
            "MATCH (u)-[:MEMBER_OF]->(o:Org)<-[:HAS_ORG]-(t:Tenant) "
            "OPTIONAL MATCH (u)-[m:MEMBER_OF]->(o) "
            "RETURN u.id AS user_id, u.tenant_id AS tenant_id, u.password_hash AS password_hash, "
            "u.can_read_source AS can_read_source, collect(DISTINCT o.id) AS org_ids, "
            "collect(DISTINCT m.role) AS roles LIMIT 1",
            email=email,
        )
        return await result.single()
    row = await cross_tenant_tx("auth.authenticate", query)
    if not row:
        # Keep the failure path computationally similar without revealing account existence.
        try:
            await asyncio.to_thread(_hasher.verify, _DUMMY_PASSWORD_HASH, password)
        except (VerifyMismatchError, InvalidHashError):
            return None
        return None
    try:
        if not await asyncio.to_thread(_hasher.verify, row["password_hash"], password):
            return None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return None
    return {key: row[key] for key in ("user_id", "tenant_id", "org_ids", "roles", "can_read_source")}


async def create_session(tenant_id: str, user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + timedelta(hours=SESSION_HOURS)
    async def query(tx):
        await (await tx.run(
            "MATCH (u:User {id:$user_id, tenant_id:$tenant_id}) "
            "CREATE (s:Session {id:$id, tenant_id:$tenant_id, user_id:$user_id, "
            "token_hash:$token_hash, csrf_token:$csrf, expires_at:datetime($expires), created_at:datetime()}) "
            "CREATE (s)-[:FOR_USER]->(u) RETURN s.id",
            id="ses_" + secrets.token_hex(16), tenant_id=tenant_id, user_id=user_id,
            token_hash=_token_hash(token), csrf=secrets.token_urlsafe(24), expires=expires.isoformat(),
        )).single(strict=True)
    await write_tx(tenant_id, query)
    return token


async def session_principal(token: str | None) -> tuple[Principal, str] | None:
    if not token:
        return None
    async def query(tx):
        result = await tx.run(
            "MATCH (s:Session {token_hash:$token_hash})-[:FOR_USER]->(u:User) "
            "WHERE s.expires_at > datetime() AND u.disabled = false "
            "MATCH (u)-[m:MEMBER_OF]->(o:Org) "
            "RETURN s.tenant_id AS tenant_id, u.id AS user_id, collect(DISTINCT o.id) AS org_ids, "
            "collect(DISTINCT m.role) AS roles, u.can_read_source AS can_read_source, s.csrf_token AS csrf",
            token_hash=_token_hash(token),
        )
        return await result.single()
    row = await cross_tenant_tx("auth.session_lookup", query)
    if not row:
        return None
    return Principal(row["tenant_id"], row["user_id"], tuple(row["org_ids"]), frozenset(row["roles"]), bool(row["can_read_source"])), row["csrf"]


async def get_principal(request: Request, token: str | None = Depends(_cookie)) -> Principal:
    current = getattr(request.state, "principal", None)
    if current:
        return current
    resolved = await session_principal(token)
    if not resolved:
        raise HTTPException(status_code=401, detail="Authentication required")
    principal, csrf = resolved
    request.state.principal = principal
    request.state.csrf_token = csrf
    request.state.session_token = token
    return principal


def require_roles(*roles: str):
    async def dependency(principal: Principal = Depends(get_principal)) -> Principal:  # noqa: B008
        if not principal.roles.intersection(roles):
            raise HTTPException(status_code=403, detail="Insufficient role")
        return principal
    return dependency


def can_view_request(principal: Principal, meta: dict[str, Any]) -> bool:
    return can(principal, "view_request", meta)


def can_review(principal: Principal, meta: dict[str, Any]) -> bool:
    return can(principal, "review", meta)


def can_read_learning_request(principal: Principal, meta: dict[str, Any]) -> bool:
    return can(principal, "learn_read", meta)


def scope_filter_cypher(principal: Principal) -> str:
    return policy_scope_filter_cypher(principal)


async def enforce_csrf(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    cached_principal = getattr(request.state, "principal", None)
    cached_csrf = getattr(request.state, "csrf_token", None)
    resolved = ((cached_principal, cached_csrf) if cached_principal and cached_csrf
                else await session_principal(request.cookies.get("jev_session")))
    if resolved:
        request.state.principal, request.state.csrf_token = resolved
        request.state.session_token = request.cookies.get("jev_session")
    supplied = request.headers.get("X-CSRF-Token")
    cookie_token = request.cookies.get("jev_csrf")
    if (not resolved or not supplied or not cookie_token
            or not secrets.compare_digest(cookie_token, supplied)
            or not secrets.compare_digest(resolved[1], supplied)):
        raise HTTPException(status_code=403, detail="CSRF validation failed")
