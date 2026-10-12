import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ildongi.auth.core import hash_password
from ildongi.auth.types import Principal
from ildongi.auth.users import UserAdminError, create_user, update_user, user_detail
from ildongi.db.driver import get_driver
from ildongi.db.schema import apply_schema
from ildongi.main import create_app

PASSWORD = "correct horse"


@pytest.mark.parametrize("disabled", [False, True])
def test_concurrent_admin_revocation_preserves_an_active_admin(admin_graph, disabled):
    tenant, _ = admin_graph
    admin_id, member_id = f"usr_{tenant}_admin", f"usr_{tenant}_member"
    admin = Principal(tenant, admin_id, (f"{tenant}_a",), frozenset({"admin"}))
    member = Principal(tenant, member_id, (f"{tenant}_a",), frozenset({"admin"}))
    body = {"version": 0, "roles": ["admin"], "org_ids": [f"{tenant}_a"],
            "disabled": False, "can_read_source": False, "reason": "관리자 배정"}

    async def exercise():
        await update_user(admin, member_id, body)
        revoke = {**body, "roles": ["admin"] if disabled else ["requester"],
                  "disabled": disabled, "reason": "권한 회수"}
        results = await asyncio.gather(
            update_user(admin, member_id, {**revoke, "version": 1}),
            update_user(member, admin_id, revoke), return_exceptions=True)
        assert sum(isinstance(result, dict) for result in results) == 1
        errors = [result for result in results if isinstance(result, UserAdminError)]
        assert len(errors) == 1 and errors[0].status_code == 403
        revoked = member if isinstance(results[0], dict) else admin
        survivor = admin if revoked == member else member
        current = (await user_detail(survivor, survivor.user_id))["user"]
        assert not current["disabled"] and "admin" in current["roles"]
        with pytest.raises(UserAdminError) as error:
            await create_user(revoked, {**body, "email": f"stale@{tenant}.test"})
        assert error.value.status_code == 403
        detail = await user_detail(survivor, revoked.user_id)
        assert sum(h["reason"] == "권한 회수" for h in detail["history"]) == 1
    asyncio.run(exercise())


@pytest.fixture
def admin_graph():
    tenant, other = f"adm_{uuid4().hex}", f"adm_{uuid4().hex}"

    async def seed():
        await apply_schema()
        driver = await get_driver()
        async with driver.session() as session:
            for t in (tenant, other):
                await (await session.run(
                    "CREATE (t:Tenant {id:$t, tenant_id:$t}), (a:Org {id:$t+'_a', tenant_id:$t, name:'a'}), "
                    "(b:Org {id:$t+'_b', tenant_id:$t, name:'b'}), (t)-[:HAS_ORG]->(a), (t)-[:HAS_ORG]->(b) "
                    "CREATE (admin:User {id:'usr_'+$t+'_admin', tenant_id:$t, email:'admin@'+$t+'.test', password_hash:$pw, disabled:false, can_read_source:false}), "
                    "(member:User {id:'usr_'+$t+'_member', tenant_id:$t, email:'member@'+$t+'.test', password_hash:$pw, disabled:false, can_read_source:false}), "
                    "(admin)-[:MEMBER_OF {role:'admin'}]->(a), (member)-[:MEMBER_OF {role:'requester'}]->(a)",
                    t=t, pw=hash_password(PASSWORD))).consume()
    asyncio.run(seed())
    yield tenant, other


def login(client: TestClient, email: str) -> str:
    assert client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200
    return client.get("/api/auth/me").json()["csrf_token"]


def test_admin_manages_roles_orgs_with_audit_version_and_tenant_scope(admin_graph):
    tenant, other = admin_graph
    member = f"usr_{tenant}_member"
    with TestClient(create_app()) as admin, TestClient(create_app()) as target:
        csrf = login(admin, f"admin@{tenant}.test")
        listed = admin.get("/api/admin/users").json()
        assert {u["user_id"] for u in listed["users"]} == {f"usr_{tenant}_admin", member}  # other tenant invisible
        assert {o["id"] for o in listed["orgs"]} == {f"{tenant}_a", f"{tenant}_b"} and "admin" in listed["roles"]
        row = next(u for u in listed["users"] if u["user_id"] == member)
        assert row["roles"] == ["requester"] and row["version"] == 0

        body = {"version": 0, "roles": ["requester", "reviewer"], "org_ids": [f"{tenant}_a", f"{tenant}_b"],
                "disabled": False, "can_read_source": True, "reason": "검토 업무 배정"}
        headers = {"X-CSRF-Token": csrf}
        changed = admin.post(f"/api/admin/users/{member}", json=body, headers=headers)
        assert changed.status_code == 200, changed.text
        assert changed.json()["version"] == 1 and changed.json()["roles"] == ["requester", "reviewer"]

        login(target, f"member@{tenant}.test")
        me = target.get("/api/auth/me").json()
        assert me["roles"] == ["requester", "reviewer"] and set(me["org_ids"]) == {f"{tenant}_a", f"{tenant}_b"}
        assert me["can_read_source"] is True

        detail = admin.get(f"/api/admin/users/{member}").json()
        assert detail["history"][0]["reason"] == "검토 업무 배정"
        assert detail["history"][0]["before"]["roles"] == ["requester"]

        assert admin.post(f"/api/admin/users/{member}", json=body, headers=headers).status_code == 409  # stale version
        bad = {**body, "version": 1}
        assert admin.post(f"/api/admin/users/{member}", json={**bad, "roles": ["root"]}, headers=headers).status_code == 422
        assert admin.post(f"/api/admin/users/{member}", json={**bad, "org_ids": [f"{other}_a"]}, headers=headers).status_code == 422
        assert admin.post(f"/api/admin/users/{member}", json={**bad, "reason": " "}, headers=headers).status_code == 422
        assert admin.post(f"/api/admin/users/usr_{other}_member", json=bad, headers=headers).status_code == 404

        disabled = admin.post(f"/api/admin/users/{member}", json={**bad, "disabled": True}, headers=headers)
        assert disabled.status_code == 200, disabled.text
        assert target.get("/api/auth/me").status_code == 401  # suspended account loses its session at once


def test_admin_cannot_lock_themselves_out_and_non_admin_is_refused(admin_graph):
    tenant, _ = admin_graph
    me = f"usr_{tenant}_admin"
    with TestClient(create_app()) as admin, TestClient(create_app()) as member:
        csrf = login(admin, f"admin@{tenant}.test")
        body = {"version": 0, "roles": ["requester"], "org_ids": [f"{tenant}_a"], "disabled": False,
                "can_read_source": False, "reason": "실수"}
        assert admin.post(f"/api/admin/users/{me}", json=body, headers={"X-CSRF-Token": csrf}).status_code == 409
        assert admin.post(f"/api/admin/users/{me}", json={**body, "roles": ["admin"], "disabled": True},
                          headers={"X-CSRF-Token": csrf}).status_code == 409

        member_csrf = login(member, f"member@{tenant}.test")
        assert member.get("/api/admin/users").status_code == 403
        assert member.post(f"/api/admin/users/{me}", json=body, headers={"X-CSRF-Token": member_csrf}).status_code == 403


def test_admin_issues_account_with_one_time_password(admin_graph):
    tenant, other = admin_graph
    with TestClient(create_app()) as admin, TestClient(create_app()) as fresh:
        csrf = login(admin, f"admin@{tenant}.test")
        headers = {"X-CSRF-Token": csrf}
        body = {"email": f"New@{tenant}.test", "display_name": "신규", "roles": ["reviewer"], "org_ids": [f"{tenant}_b"],
                "reason": "입사"}
        issued = admin.post("/api/admin/users", json=body, headers=headers)
        assert issued.status_code == 201, issued.text
        password = issued.json()["temporary_password"]
        assert len(password) >= 12 and issued.json()["user"]["email"] == f"new@{tenant}.test"

        assert fresh.post("/api/auth/login", json={"email": f"new@{tenant}.test", "password": password}).status_code == 200
        me = fresh.get("/api/auth/me").json()
        assert me["tenant_id"] == tenant and me["roles"] == ["reviewer"] and me["org_ids"] == [f"{tenant}_b"]

        user_id = issued.json()["user"]["user_id"]
        history = admin.get(f"/api/admin/users/{user_id}").json()["history"]
        assert history[0]["action"] == "user.create" and history[0]["reason"] == "입사"
        assert "temporary_password" not in str(history) and password not in str(history)

        assert admin.post("/api/admin/users", json=body, headers=headers).status_code == 409  # duplicate email
        assert admin.post("/api/admin/users", json={**body, "email": f"member@{other}.test"}, headers=headers).status_code == 409
        assert admin.post("/api/admin/users", json={**body, "email": "not-an-email"}, headers=headers).status_code == 422
        assert admin.post("/api/admin/users", json={**body, "email": f"x@{tenant}.test", "org_ids": [f"{other}_a"]},
                          headers=headers).status_code == 422

        member_csrf = login(fresh, f"member@{tenant}.test")
        assert fresh.post("/api/admin/users", json={**body, "email": f"y@{tenant}.test"},
                          headers={"X-CSRF-Token": member_csrf}).status_code == 403
