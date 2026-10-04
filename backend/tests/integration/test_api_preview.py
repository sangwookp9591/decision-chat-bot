from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from jevtriage.auth.core import get_principal
from jevtriage.auth.policy import can
from jevtriage.auth.types import Principal
from jevtriage.db.driver import get_driver
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.ingest.store import create_request
from jevtriage.main import create_app

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
async def preview_tenant():
    tenant = f"preview_{uuid4().hex}"
    await apply_schema()
    yield tenant
    driver = await get_driver()
    async with driver.session() as session:
        await (await session.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=tenant)).consume()


async def _http_client(tenant, principal):
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: principal
    return TestClient(app)


async def test_request_preview_masking_and_owner_permissions(preview_tenant):
    tenant = preview_tenant
    owner = Principal(tenant, "owner", (), frozenset({"requester"}), False)
    peer = Principal(tenant, "peer", (), frozenset({"requester"}), False)
    card_prefix = [4] + [1] * 14
    checksum = 0
    for index, digit in enumerate(reversed(card_prefix)):
        doubled = digit * 2
        checksum += (doubled - 9 if doubled > 9 else doubled) if index % 2 == 0 else digit
    card = "".join(map(str, card_prefix + [(10 - checksum % 10) % 10]))
    key = "sk_test_" + "a1b2c3d4e5f6g7h8i9j0"
    resident = "900101" + "3" + "123456"
    phone = "010" + "-" + "1234" + "-" + "5678"
    email = "preview" + "@example.invalid"
    text = f"Contact {email} or {phone}, id {resident}, card {card}, key {key}. Details follow."
    result = await create_request(
        tenant, owner.user_id, text, [], f"key_{uuid4().hex}", f"hash_{uuid4().hex}",
        datetime.now(UTC).isoformat(), org_ids=("org-preview",),
    )
    request_id = result["request_id"]
    client = await _http_client(tenant, owner)
    with client:
        listed = client.get("/api/requests").json()["items"]
        item = next(row for row in listed if row["id"] == request_id)
        assert item["title"].startswith("Contact [MASKED_")
        assert len(item["title"]) <= 60
        assert len(item["preview"]) <= 140
        for sensitive in (email, phone, resident, card, key):
            assert sensitive not in item["preview"]
        detail = client.get(f"/api/requests/{request_id}").json()
        assert detail["request"]["title"] == item["title"]
        assert detail["request"]["preview"] == item["preview"]
        assert text in detail["revisions"][0]["text"]
        document = client.get(f"/api/requests/{request_id}/revisions/1/document?source=chat").json()
        assert email in "".join(unit.get("text", "") for unit in document["units"])

    assert can(owner, "request:read", {"tenant_id": tenant, "created_by": owner.user_id})
    assert not can(peer, "request:read", {"tenant_id": tenant, "created_by": owner.user_id})

    async def stored(tx):
        row = await (await tx.run(
            "MATCH (r:Request {id:$id,tenant_id:$tenant}) RETURN r.title AS title,r.preview AS preview",
            id=request_id, tenant=tenant,
        )).single(strict=True)
        return dict(row)

    values = await read_tx(tenant, stored)
    assert values["title"] == item["title"]
    assert values["preview"] == item["preview"]

    reviewer = Principal(tenant, "reviewer", ("org-preview",), frozenset({"reviewer"}), False)
    reviewer_client = await _http_client(tenant, reviewer)
    with reviewer_client:
        reviewer_item = next(row for row in reviewer_client.get("/api/requests").json()["items"]
                             if row["id"] == request_id)
        assert "title" in reviewer_item
        assert "preview" not in reviewer_item
        reviewer_detail = reviewer_client.get(f"/api/requests/{request_id}").json()
        assert "preview" not in reviewer_detail["request"]
        assert "text" not in reviewer_detail["revisions"][0]

    operator = Principal(tenant, "operator", (), frozenset({"operator"}), False)
    restricted = await _http_client(tenant, operator)
    with restricted:
        restricted_item = next(row for row in restricted.get("/api/requests").json()["items"]
                               if row["id"] == request_id)
        assert "title" in restricted_item
        assert "preview" not in restricted_item
        hidden = restricted.get(f"/api/requests/{request_id}").json()
        assert "text" not in hidden["revisions"][0]
        assert "preview" not in hidden["request"]

    isolated = await _http_client(f"other_{tenant}", operator.__class__(
        f"other_{tenant}", "operator", (), frozenset({"operator"}), False,
    ))
    with isolated:
        assert all(row["id"] != request_id for row in isolated.get("/api/requests").json()["items"])

    revised_id = (await create_request(
        tenant, owner.user_id, "Original.", [], f"key_{uuid4().hex}",
        f"hash_{uuid4().hex}", datetime.now(UTC).isoformat(),
    ))["request_id"]
    revise = await _http_client(tenant, owner)
    with revise:
        updated = revise.post(
            f"/api/requests/{revised_id}/revisions",
            data={"expected_revision": 1, "text": "Added details in this revision."},
            headers={"Idempotency-Key": f"rev_{uuid4().hex}"},
        )
        assert updated.status_code == 202
        current = next(row for row in revise.get("/api/requests").json()["items"]
                       if row["id"] == revised_id)
        assert current["title"] == "Original."
        assert "Added details in this revision." in current["preview"]


async def test_legacy_preview_backfill_runs_once(preview_tenant, monkeypatch):
    from jevtriage.ingest import store

    tenant = preview_tenant
    owner = Principal(tenant, "owner", (), frozenset({"requester"}), False)
    result = await create_request(
        tenant, owner.user_id, "Legacy request title.", [], f"key_{uuid4().hex}",
        f"hash_{uuid4().hex}", datetime.now(UTC).isoformat(),
    )
    request_id = result["request_id"]

    async def remove_fields(tx):
        await (await tx.run(
            "MATCH (r:Request {id:$id,tenant_id:$tenant}) REMOVE r.title,r.preview",
            id=request_id, tenant=tenant,
        )).consume()

    await write_tx(tenant, remove_fields)
    original = store._display_fields
    calls = 0

    def count_calls(text):
        nonlocal calls
        calls += 1
        return original(text)

    monkeypatch.setattr(store, "_display_fields", count_calls)
    client = await _http_client(tenant, owner)
    with client:
        first = client.get("/api/requests").json()["items"]
        second = client.get("/api/requests").json()["items"]
    assert calls == 1
    row = next(item for item in first if item["id"] == request_id)
    assert row["title"] == "Legacy request title."
    assert next(item for item in second if item["id"] == request_id)["preview"] == row["preview"]
