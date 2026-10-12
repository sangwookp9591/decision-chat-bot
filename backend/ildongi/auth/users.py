"""Tenant account administration: issuing accounts, roles, org memberships, source access and account suspension.

Roles live on MEMBER_OF edges (one edge per org × role), so an update rewrites the user's edges as the cross product of the
requested orgs and roles. Every change is version-checked, audited, and an admin can never lock themselves out.
"""
from __future__ import annotations

import asyncio
import json
import re
import secrets
from typing import Any
from uuid import uuid4

from neo4j.exceptions import ConstraintError

from ildongi.auth.core import hash_password
from ildongi.auth.policy import ROLES, can
from ildongi.auth.types import Principal
from ildongi.db.audit import append_audit_in_tx
from ildongi.db.tx import read_tx, write_tx

_USER_FIELDS = (
    "u.id AS user_id, u.email AS email, u.display_name AS display_name, coalesce(u.disabled,false) AS disabled, "
    "coalesce(u.can_read_source,false) AS can_read_source, coalesce(u.version,0) AS version, "
    "[x IN collect(DISTINCT m.role) WHERE x IS NOT NULL] AS roles, [x IN collect(DISTINCT o.id) WHERE x IS NOT NULL] AS org_ids"
)


class UserAdminError(Exception):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


def _require_admin(principal: Principal) -> None:
    if not can(principal, "user_admin", {"tenant_id": principal.tenant_id}):
        raise UserAdminError("계정 관리 권한이 없습니다", 403)


def _user(row: Any) -> dict:
    roles = [r for r in ROLES if r in set(row["roles"])]  # stable, documented order
    return {"user_id": row["user_id"], "email": row["email"], "display_name": row["display_name"],
            "disabled": bool(row["disabled"]), "can_read_source": bool(row["can_read_source"]),
            "version": int(row["version"]), "roles": roles, "org_ids": sorted(row["org_ids"])}


def _state(user: dict) -> dict:
    return {k: user[k] for k in ("roles", "org_ids", "disabled", "can_read_source")}


def _membership(body: dict) -> tuple[list[str], list[str], str]:
    reason = (body.get("reason") or "").strip()
    roles = sorted(set(body.get("roles") or ()))
    org_ids = sorted(set(body.get("org_ids") or ()))
    if not reason:
        raise UserAdminError("변경 사유를 입력하세요")
    if not roles or not set(roles) <= set(ROLES):
        raise UserAdminError("역할을 하나 이상, 정의된 역할 중에서 고르세요")
    if not org_ids:
        raise UserAdminError("소속 조직을 하나 이상 고르세요")
    return [r for r in ROLES if r in roles], org_ids, reason


async def _check_orgs(tx, org_ids: list[str]) -> None:
    known = {r["id"] async for r in await tx.run(
        "MATCH (o:Org {tenant_id:$tenant}) WHERE o.id IN $ids RETURN o.id AS id", ids=org_ids)}
    if known != set(org_ids):
        raise UserAdminError("이 테넌트에 없는 조직입니다")


async def list_users(principal: Principal) -> dict:
    _require_admin(principal)

    async def op(tx):
        users = [_user(row) async for row in await tx.run(
            "MATCH (u:User {tenant_id:$tenant}) "
            "OPTIONAL MATCH (u)-[m:MEMBER_OF]->(o:Org {tenant_id:$tenant}) "
            f"WITH u, m, o ORDER BY u.email RETURN {_USER_FIELDS}")]
        orgs = [{"id": row["id"], "name": row["name"]} async for row in await tx.run(
            "MATCH (o:Org {tenant_id:$tenant}) RETURN o.id AS id, coalesce(o.name, o.id) AS name ORDER BY o.id")]
        return {"users": sorted(users, key=lambda u: (u["email"] or u["user_id"])), "orgs": orgs, "roles": list(ROLES)}
    return await read_tx(principal.tenant_id, op)


async def user_detail(principal: Principal, user_id: str) -> dict:
    _require_admin(principal)

    async def op(tx):
        row = await (await tx.run(
            "MATCH (u:User {tenant_id:$tenant, id:$id}) "
            f"OPTIONAL MATCH (u)-[m:MEMBER_OF]->(o:Org {{tenant_id:$tenant}}) RETURN {_USER_FIELDS}", id=user_id)).single()
        if row is None:
            raise UserAdminError("계정을 찾을 수 없습니다", 404)
        history = [{"id": h["id"], "actor_id": h["actor_id"], "action": h["action"], "reason": h["reason"],
                    "before": json.loads(h["before"]) if h["before"] else None,
                    "after": json.loads(h["after"]) if h["after"] else None, "at": h["at"]}
                   async for h in await tx.run(
                       "MATCH (a:Audit {tenant_id:$tenant, target_type:'User', target_id:$id}) "
                       "RETURN a.id AS id, a.actor_id AS actor_id, a.action AS action, a.reason AS reason, "
                       "a.before_json AS before, a.after_json AS after, toString(a.created_at) AS at "
                       "ORDER BY a.created_at DESC LIMIT 20", id=user_id)]
        return {"user": _user(row), "history": history}
    return await read_tx(principal.tenant_id, op)


async def update_user(principal: Principal, user_id: str, body: dict) -> dict:
    _require_admin(principal)
    roles, org_ids, reason = _membership(body)
    disabled, can_read_source = bool(body.get("disabled")), bool(body.get("can_read_source"))
    if user_id == principal.user_id and ("admin" not in roles or disabled):
        raise UserAdminError("내 계정의 관리자 역할을 빼거나 사용 중지할 수 없습니다", 409)

    async def op(tx):
        # Take the user's write lock before reading so two admins cannot both pass the version check.
        row = await (await tx.run(
            "MATCH (u:User {tenant_id:$tenant, id:$id}) SET u._lock=randomUUID() WITH u "
            f"OPTIONAL MATCH (u)-[m:MEMBER_OF]->(o:Org {{tenant_id:$tenant}}) RETURN {_USER_FIELDS}", id=user_id)).single()
        if row is None:
            raise UserAdminError("계정을 찾을 수 없습니다", 404)
        before = _user(row)
        if body.get("version") != before["version"]:
            raise UserAdminError("다른 관리자가 먼저 변경했습니다. 새로고침 후 다시 시도하세요", 409)
        await _check_orgs(tx, org_ids)
        after = {"roles": [r for r in ROLES if r in roles], "org_ids": org_ids,
                 "disabled": disabled, "can_read_source": can_read_source}
        if after == _state(before):
            raise UserAdminError("바뀐 내용이 없습니다")
        version = before["version"] + 1
        await (await tx.run(
            "MATCH (u:User {tenant_id:$tenant, id:$id}) "
            "OPTIONAL MATCH (u)-[m:MEMBER_OF]->(:Org {tenant_id:$tenant}) DELETE m "
            "WITH DISTINCT u "
            "SET u.disabled=$disabled, u.can_read_source=$source, u.version=$version, "
            "u.updated_at=datetime(), u.updated_by=$actor "
            "WITH u UNWIND $orgs AS org_id MATCH (o:Org {tenant_id:$tenant, id:org_id}) "
            "UNWIND $roles AS role MERGE (u)-[:MEMBER_OF {role:role}]->(o)",
            id=user_id, disabled=disabled, source=can_read_source, version=version, actor=principal.user_id,
            orgs=org_ids, roles=after["roles"])).consume()
        if disabled and not before["disabled"]:
            await (await tx.run("MATCH (s:Session {tenant_id:$tenant, user_id:$id}) DETACH DELETE s", id=user_id)).consume()
        await append_audit_in_tx(tx, principal.tenant_id, principal.user_id, "user.update", "User", user_id,
                                 _state(before), after, reason)
        return {**before, **after, "version": version}
    return await write_tx(principal.tenant_id, op)


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


async def create_user(principal: Principal, body: dict) -> dict:
    """Issue an account with a one-time temporary password. The password is returned once and only its hash is stored."""
    _require_admin(principal)
    email = (body.get("email") or "").strip().lower()
    display_name = (body.get("display_name") or "").strip() or None
    if not _EMAIL.match(email):
        raise UserAdminError("올바른 이메일을 입력하세요")
    roles, org_ids, reason = _membership(body)
    can_read_source = bool(body.get("can_read_source"))
    temporary_password = secrets.token_urlsafe(12)
    password_hash = await asyncio.to_thread(hash_password, temporary_password)
    user_id = f"usr_{uuid4().hex}"

    async def op(tx):
        await _check_orgs(tx, org_ids)
        await (await tx.run(
            "CREATE (u:User {id:$id, tenant_id:$tenant, email:$email, display_name:$name, password_hash:$hash, "
            "disabled:false, can_read_source:$source, version:0, created_at:datetime(), created_by:$actor}) "
            "WITH u UNWIND $orgs AS org_id MATCH (o:Org {tenant_id:$tenant, id:org_id}) "
            "UNWIND $roles AS role MERGE (u)-[:MEMBER_OF {role:role}]->(o)",
            id=user_id, email=email, name=display_name, hash=password_hash, source=can_read_source,
            actor=principal.user_id, orgs=org_ids, roles=roles)).consume()
        after = {"roles": roles, "org_ids": org_ids, "disabled": False, "can_read_source": can_read_source}
        await append_audit_in_tx(tx, principal.tenant_id, principal.user_id, "user.create", "User", user_id,
                                 None, {**after, "email": email}, reason)
        return {"user_id": user_id, "email": email, "display_name": display_name, "version": 0, **after}
    try:
        user = await write_tx(principal.tenant_id, op)
    except ConstraintError as exc:  # email is unique across tenants because login resolves the tenant from it
        raise UserAdminError("이미 사용 중인 이메일입니다", 409) from exc
    return {"user": user, "temporary_password": temporary_password}
