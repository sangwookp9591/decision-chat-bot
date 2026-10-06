from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ildongi.auth.core import hash_password
from ildongi.db.driver import get_driver
from ildongi.db.schema import apply_schema
from ildongi.main import create_app


@pytest.fixture
def auth_graph():
    import asyncio
    tenant = f"auth_{uuid4().hex}"

    async def seed():
        await apply_schema()
        driver = await get_driver()
        async with driver.session() as session:
            await (await session.run(
                "CREATE (t:Tenant {id:$tenant, tenant_id:$tenant}), "
                "(o:Org {id:$org, tenant_id:$tenant}), "
                "(u:User {id:$user, tenant_id:$tenant, email:$email, password_hash:$password, disabled:false, can_read_source:false}), "
                "(u)-[:MEMBER_OF {role:'requester'}]->(o), (t)-[:HAS_ORG]->(o)",
                tenant=tenant, org=f"{tenant}_org", user=f"usr_{tenant}", email=f"{tenant}@test", password=hash_password("correct horse"),
            )).consume()
    asyncio.run(seed())
    yield tenant


def test_login_me_csrf_logout_and_expiry(auth_graph):
    with TestClient(create_app()) as client:
        assert client.post("/api/auth/login", json={"email": f"{auth_graph}@test", "password": "wrong"}).status_code == 401
        assert client.post("/api/auth/login", json={"email": f"{auth_graph}@test", "password": "correct horse"}).status_code == 200
        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["tenant_id"] == auth_graph
        assert client.post("/api/auth/logout").status_code == 403
        csrf = me.json()["csrf_token"]
        assert client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
        assert client.get("/api/auth/me").status_code == 401

        assert client.post("/api/auth/login", json={"email": f"{auth_graph}@test", "password": "correct horse"}).status_code == 200
        import asyncio

        from ildongi.auth.core import _token_hash
        from ildongi.db.driver import get_driver
        token = client.cookies.get("ildongi_session")
        async def expire():
            driver = await get_driver()
            async with driver.session() as session:
                await (await session.run("MATCH (s:Session {token_hash:$hash}) SET s.expires_at=datetime() - duration('PT1S')", hash=_token_hash(token))).consume()
        asyncio.run(expire())
        assert client.get("/api/auth/me").status_code == 401


def test_scope_and_operator_source_policy(auth_graph):
    from ildongi.auth.core import Principal, can_view_request, scope_filter_cypher
    requester = Principal(auth_graph, "u1", ("org-a",), frozenset({"requester"}), False)
    operator = Principal(auth_graph, "u2", (), frozenset({"operator"}), False)
    meta = {"tenant_id": auth_graph, "created_by": "u1", "org_ids": []}
    assert can_view_request(requester, meta)
    assert not can_view_request(requester, {**meta, "tenant_id": "other"})
    assert "tenant_id = $tenant_id" in scope_filter_cypher(requester)
    assert can_view_request(operator, meta) and not operator.can_read_source


def test_parallel_first_failed_logins_create_one_counter_and_count_every_attempt(auth_graph):
    from concurrent.futures import ThreadPoolExecutor

    from ildongi.db.driver import get_driver

    email = f"{auth_graph}@test"
    with TestClient(create_app()) as client, ThreadPoolExecutor(max_workers=20) as pool:
        responses = list(pool.map(lambda _: client.post(
            "/api/auth/login", json={"email": email, "password": "wrong"}), range(20)))
    assert sum(response.status_code == 401 for response in responses) == 10
    assert sum(response.status_code == 429 for response in responses) == 10
    import asyncio
    async def inspect():
        driver = await get_driver()
        async with driver.session() as session:
            rows = await (await session.run(
                "MATCH (l:LoginAttempt {tenant_id:$tenant,email:$email}) "
                "RETURN count(l) AS nodes,max(l.count) AS attempts",
                tenant=auth_graph,email=email,
            )).single(strict=True)
            return rows["nodes"], rows["attempts"]
    assert asyncio.run(inspect()) == (1, 20)
