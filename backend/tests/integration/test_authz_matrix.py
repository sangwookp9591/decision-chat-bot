"""Authorization contract and regressions for review and source exposure."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi.testclient import TestClient

from jevtriage.auth.core import Principal, can_review, hash_password
from jevtriage.db.driver import get_driver
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import write_tx
from jevtriage.ingest import api as ingest_api
from jevtriage.main import create_app
from jevtriage.review.api import DecisionCommand, _allowed, review_decision
from jevtriage.review.service import required_reviewer_org
from tests.integration.test_review_assignment import sample


@pytest_asyncio.fixture
async def review_tenant():
    tenant_id = f"review_authz_{uuid4().hex}"
    await apply_schema()
    async def setup(tx):
        for name in ("ai", "it", "business"):
            await (await tx.run(
                "CREATE (:Org {id:$id,tenant_id:$tenant,name:$name})",
                id=f"{tenant_id}-{name}", tenant=tenant_id, name=name,
            )).consume()
    await write_tx(tenant_id, setup)
    yield tenant_id
    async def cleanup(tx):
        await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n",
                            tenant=tenant_id)).consume()
    await write_tx(tenant_id, cleanup)


@pytest.mark.parametrize("role,org,allowed", [
    ("reviewer", "tenant-ai", True),
    ("reviewer", "tenant-it", False),
    ("team_member", "tenant-ai", False),
    ("team_member", "tenant-it", False),
])
def test_review_requires_assigned_org_and_reviewer_role(role, org, allowed):
    principal = Principal("tenant", "someone", (org,), frozenset({role}))
    request = {"tenant_id": "tenant", "created_by": "owner", "org_ids": ["tenant-ai"]}
    review = {"required_reviewer_org": "검토자"}
    assert _allowed(principal, review, request) is allowed
    assert can_review(principal, {**request, "required_reviewer_org": "tenant-ai"}) is allowed


def test_review_fallback_has_stable_org():
    assert required_reviewer_org("tenant", "검토자", ("tenant-it",)) == "tenant-ai"
    assert required_reviewer_org("tenant", "검토자", ("tenant-ai",)) == "tenant-ai"


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("role,org", [("reviewer", "it"), ("team_member", "ai")])
async def test_review_decision_denies_wrong_org_or_role(review_tenant, role, org):
    tenant = review_tenant
    _, review_id, command = await sample(tenant)
    async def legacy_review(tx):
        await (await tx.run(
            "MATCH (v:Review {tenant_id:$tenant,id:$id}) "
            "SET v.required_reviewer_org='검토자'",
            tenant=tenant, id=review_id,
        )).consume()
    await write_tx(tenant, legacy_review)
    principal = Principal(tenant, "outsider", (f"{tenant}-{org}",), frozenset({role}))
    with pytest.raises(HTTPException) as error:
        await review_decision(review_id, DecisionCommand(**command),
                              idempotency_key=str(uuid4()), principal=principal)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_request_detail_redacts_revision_text(monkeypatch):
    async def visible_detail(_principal, _request_id):
        return {"request": {"id": "r", "status": "ready"},
                "revisions": [{"id": "rev", "text": "SECRET", "text_hash": "digest"}],
                "attachments": [{"id": "file", "path": "/private/file"}]}
    monkeypatch.setattr(ingest_api.service, "visible_detail", visible_detail)
    monkeypatch.setattr(ingest_api.service, "_journal", lambda *args, **kwargs: None)
    principal = Principal("tenant", "operator", (), frozenset({"operator"}), False)
    result = await ingest_api.request_detail("r", principal)
    assert "text" not in result["revisions"][0]
    assert "SECRET" not in str(result)
    assert result["revisions"][0]["text_hash"] == "digest"


@pytest.mark.parametrize("role,org,source,expected", [
    ("requester", "tenant-ai", False, 200),
    ("reviewer", "tenant-ai", False, 200),
    ("reviewer", "tenant-it", False, 404),
    ("team_member", "tenant-ai", False, 200),
    ("operator", "tenant-it", False, 200),
    ("policy_editor", "tenant-it", False, 404),
    ("rule_admin", "tenant-it", False, 404),
])
def test_request_access_matrix(role, org, source, expected):
    from jevtriage.auth.policy import can
    principal = Principal("tenant", "other", (org,), frozenset({role}), source)
    meta = {"tenant_id": "tenant", "created_by": "owner", "org_ids": ["tenant-ai"]}
    assert (200 if can(principal, "view_request", meta) else 404) == expected
    assert not can(principal, "view_request", {**meta, "tenant_id": "elsewhere"})
    assert can(principal, "read_source", meta) is False


def test_source_redaction_nested_payload():
    from jevtriage.auth.policy import redact_source
    principal = Principal("tenant", "operator", (), frozenset({"operator"}), False)
    payload = {"revisions": [{"text": "SECRET", "text_hash": "hash"}],
               "outputs": [{"evidence": [{"source_text": "SECRET"}]}]}
    result = redact_source(principal, payload)
    assert "SECRET" not in str(result)
    assert result["revisions"][0]["text_hash"] == "hash"


@pytest.mark.parametrize("action,role,org,source,expected", [
    ("view_request", "requester", "ai", False, 200),
    ("read_source", "requester", "ai", False, 403),
    ("read_source", "reviewer", "ai", True, 200),
    ("review", "reviewer", "ai", False, 200),
    ("review", "reviewer", "it", False, 403),
    ("review", "team_member", "ai", False, 403),
    ("view_task", "team_member", "ai", False, 200),
    ("view_task", "team_member", "it", False, 403),
    ("transition_task", "team_member", "ai", False, 200),
    ("transition_task", "reviewer", "ai", False, 403),
    ("view_trace", "operator", "it", False, 200),
    ("view_graph", "reviewer", "ai", False, 200),
    ("view_graph", "requester", "ai", False, 403),
    ("policy_edit", "policy_editor", "ai", False, 200),
    ("policy_edit", "operator", "ai", False, 403),
    ("learn_admin", "rule_admin", "it", False, 200),
    ("learn_admin", "reviewer", "ai", False, 403),
    ("learn_admin", "team_member", "ai", False, 403),
    ("monitoring_read", "operator", "it", False, 200),
    ("monitoring_read", "rule_admin", "ai", False, 403),
])
def test_action_status_matrix(action, role, org, source, expected):
    from jevtriage.auth.policy import can
    principal = Principal("tenant", "other", (f"tenant-{org}",), frozenset({role}), source)
    meta = {"tenant_id": "tenant", "created_by": "owner", "org_ids": ["tenant-ai"],
            "required_reviewer_org": "tenant-ai", "task_org_ids": ["tenant-ai"]}
    status = 200 if can(principal, action, meta) else 403
    assert status == expected
    assert not can(principal, action, {**meta, "tenant_id": "other"})


ROLE_CONTRACT = {
    "requester": ("requester", "ai", False),
    "reviewer_match": ("reviewer", "ai", False),
    "reviewer_other": ("reviewer", "it", False),
    "team_member": ("team_member", "ai", False),
    "operator_no_source": ("operator", "it", False),
    "operator_source": ("operator", "it", True),
    "policy_editor": ("policy_editor", "it", False),
    "rule_admin": ("rule_admin", "it", False),
}
REQUEST_READERS = {"requester", "reviewer_match", "team_member",
                   "operator_no_source", "operator_source"}
ENDPOINT_CONTRACT = [
    ("GET /api/requests/{id}", "view_request", REQUEST_READERS),
    ("GET /api/requests/{id}/evidence/{span}", "read_source", {"operator_source"}),
    ("GET /api/requests/{id}/judgment", "view_request", REQUEST_READERS),
    ("POST /api/reviews/{id}/decision", "review", {"reviewer_match"}),
    ("GET /api/tasks/{id}", "view_task", REQUEST_READERS),
    ("POST /api/tasks/{id}/transition", "transition_task", {"team_member"}),
    ("GET /api/steps/{id}", "view_trace", REQUEST_READERS),
    ("GET /api/graph/judgment", "view_graph",
     {"reviewer_match", "operator_no_source", "operator_source"}),
    ("POST /api/policy/publish", "policy_edit", {"policy_editor"}),
    ("POST /api/learning/rules/{id}/versions/{version}/publish", "learn_admin",
     {"rule_admin"}),
    ("GET /api/monitoring/summary", "monitoring_read",
     {"operator_no_source", "operator_source"}),
]


@pytest.mark.parametrize("endpoint,action,allowed", ENDPOINT_CONTRACT,
                         ids=[row[0] for row in ENDPOINT_CONTRACT])
@pytest.mark.parametrize("role_name", ROLE_CONTRACT)
@pytest.mark.parametrize("same_tenant", [True, False], ids=["same-tenant", "other-tenant"])
def test_endpoint_authorization_contract(endpoint, action, allowed, role_name, same_tenant):
    from jevtriage.auth.policy import can
    role, org, source = ROLE_CONTRACT[role_name]
    principal = Principal("tenant", "actor", (f"tenant-{org}",), frozenset({role}), source)
    meta = {"tenant_id": "tenant" if same_tenant else "other", "created_by": "owner",
            "org_ids": ["tenant-ai"], "required_reviewer_org": "tenant-ai",
            "task_org_ids": ["tenant-ai"]}
    # Read endpoints hide inaccessible resources; mutations report forbidden.
    denied = 404 if endpoint.startswith(("GET /api/requests/", "GET /api/tasks/")) else 403
    expected = 200 if same_tenant and role_name in allowed else denied
    actual = 200 if can(principal, action, meta) else denied
    assert actual == expected, (endpoint, role_name, same_tenant)


@pytest.mark.parametrize("role", ["requester", "operator"])
def test_list_cypher_matches_single_request_policy(role):
    from jevtriage.auth.policy import can, scope_filter_cypher
    principal = Principal("tenant", "owner", ("tenant-ai",), frozenset({role}))
    metas = [
        {"id": "owner", "tenant_id": "tenant", "created_by": "owner", "org_ids": []},
        {"id": "direct", "tenant_id": "tenant", "created_by": "else", "org_ids": ["tenant-ai"]},
        {"id": "shared", "tenant_id": "tenant", "created_by": "else", "org_ids": ["tenant-it"],
         "shared_org_ids": ["tenant-ai"]},
        {"id": "hidden", "tenant_id": "tenant", "created_by": "else", "org_ids": ["tenant-it"]},
        {"id": "cross", "tenant_id": "other", "created_by": "owner", "org_ids": ["tenant-ai"]},
    ]
    expected = {meta["id"] for meta in metas if can(principal, "view_request", meta)}
    async def query():
        driver = await get_driver()
        async with driver.session() as session:
            rows = await (await session.run(
                f"UNWIND $metas AS r WITH r WHERE {scope_filter_cypher(principal)} RETURN r.id AS id",
                metas=metas, tenant_id=principal.tenant_id, user_id=principal.user_id,
                org_ids=list(principal.org_ids),
            )).data()
        return {row["id"] for row in rows}
    assert asyncio.run(query()) == expected


def test_unknown_account_uses_same_login_counter_shape():
    email = f"missing_{uuid4().hex}@test"
    with TestClient(create_app()) as client:
        for _ in range(10):
            assert client.post("/api/auth/login", json={"email": email, "password": "wrong"}).status_code == 401
        assert client.post("/api/auth/login", json={"email": email, "password": "wrong"}).status_code == 429
    async def inspect():
        driver = await get_driver()
        async with driver.session() as session:
            row = await (await session.run(
                "MATCH (l:LoginAttempt {tenant_id:'unknown',email:$email}) "
                "RETURN l.count AS count,l.window_start AS started",
                email=email,
            )).single()
            await (await session.run(
                "MATCH (l:LoginAttempt {tenant_id:'unknown',email:$email}) DETACH DELETE l",
                email=email,
            )).consume()
        return row
    row = asyncio.run(inspect())
    assert row["count"] == 10 and row["started"] is not None


def test_login_limit_blocks_correct_password_until_window_expires():
    tenant = f"authz_{uuid4().hex}"
    email = f"{tenant}@test"
    async def seed():
        await apply_schema()
        driver = await get_driver()
        async with driver.session() as session:
            await (await session.run(
                "CREATE (t:Tenant {id:$tenant,tenant_id:$tenant}),"
                "(o:Org {id:$org,tenant_id:$tenant}),"
                "(u:User {id:$user,tenant_id:$tenant,email:$email,password_hash:$hash,"
                "disabled:false,can_read_source:false}),"
                "(t)-[:HAS_ORG]->(o),(u)-[:MEMBER_OF {role:'requester'}]->(o)",
                tenant=tenant, org=f"{tenant}-ai", user=f"usr_{tenant}", email=email,
                hash=hash_password("correct"),
            )).consume()
    asyncio.run(seed())
    try:
        with TestClient(create_app()) as client:
            for _ in range(10):
                assert client.post("/api/auth/login", json={"email": email, "password": "bad"}).status_code == 401
            assert client.post("/api/auth/login", json={"email": email, "password": "correct"}).status_code == 429
            async def expire():
                driver = await get_driver()
                async with driver.session() as session:
                    await (await session.run(
                        "MATCH (l:LoginAttempt {tenant_id:$tenant,email:$email}) "
                        "SET l.window_start=datetime() - duration('PT16M')",
                        tenant=tenant, email=email,
                    )).consume()
            asyncio.run(expire())
            assert client.post("/api/auth/login", json={"email": email, "password": "correct"}).status_code == 200
    finally:
        async def cleanup():
            driver = await get_driver()
            async with driver.session() as session:
                await (await session.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=tenant)).consume()
        asyncio.run(cleanup())


@pytest.mark.asyncio
async def test_sse_rechecks_revoked_session(monkeypatch):
    from jevtriage.events import router as events
    principal = Principal("tenant", "user", ("tenant-ai",), frozenset({"requester"}))
    async def read_tx(_tenant, callback):
        return 0, None, None, None  # head, retained_from, oldest, cursor_created
    async def subscribe(_tenant, _cursor):
        return object(), asyncio.Queue()
    async def unsubscribe(_hub, _queue):
        return None
    async def revoked(_token):
        return None
    class Request:
        def __init__(self):
            self.headers = {}
            self.cookies = {"jev_session": "revoked"}
        async def is_disconnected(self):
            return False
    monkeypatch.setattr(events, "read_tx", read_tx)
    monkeypatch.setattr(events, "_subscribe", subscribe)
    monkeypatch.setattr(events, "_unsubscribe", unsubscribe)
    monkeypatch.setattr(events, "session_principal", revoked, raising=False)
    monkeypatch.setattr(events, "SESSION_RECHECK_SECONDS", 0, raising=False)
    response = await events.stream_events(Request(), after=0, max_events=None, principal=principal)
    first = await asyncio.wait_for(anext(response.body_iterator), timeout=2)
    assert b"event: session-expired" in first
    await response.body_iterator.aclose()


@pytest.mark.asyncio
async def test_sse_reconnect_header_overrides_url_cursor_without_duplicates(monkeypatch):
    from jevtriage.events import router as events
    principal = Principal("tenant", "owner", (), frozenset({"requester"}))
    now = datetime.now(UTC)
    batch = [{"seq": seq, "request_id": "req", "run_id": "run", "kind": "progress",
              "payload": {"status": str(seq)}, "created_at": now} for seq in (4, 5, 6)]
    queue = asyncio.Queue()
    queue.put_nowait((batch, {"req": {"tenant_id": "tenant", "created_by": "owner"}}, 6))
    class Hub:
        def __init__(self):
            self.subscribers = {queue: 5}
    async def read_tx(_tenant, _callback):
        return 10, None, None, None  # head, retained_from, oldest, cursor_created
    async def subscribe(_tenant, cursor):
        assert cursor == 5
        return Hub(), queue
    async def unsubscribe(_hub, _queue):
        return None
    class Request:
        def __init__(self):
            self.headers = {"last-event-id": "5"}
            self.cookies = {}
        async def is_disconnected(self):
            return False
    monkeypatch.setattr(events, "read_tx", read_tx)
    monkeypatch.setattr(events, "_subscribe", subscribe)
    monkeypatch.setattr(events, "_unsubscribe", unsubscribe)
    monkeypatch.setattr(events._journal, "append", lambda _entry: None)
    response = await events.stream_events(Request(), after=2, max_events=1, principal=principal)
    assert response.status_code == 200
    chunks = [chunk async for chunk in response.body_iterator]
    assert len(chunks) == 1
    assert b"id: 6\n" in chunks[0]
    assert b"id: 5\n" not in chunks[0]
