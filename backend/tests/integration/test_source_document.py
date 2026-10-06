"""Source document viewer endpoint: unit list always, raw text only with read_source."""
from uuid import uuid4

import pytest
import pytest_asyncio

from ildongi.db.driver import get_driver
from ildongi.db.schema import apply_schema
from ildongi.db.tx import read_tx
from tests.integration.test_ingest_api import _http_client

pytestmark = pytest.mark.asyncio(loop_scope="session")

SECRET = "SECRET-LINE-TWO"


@pytest_asyncio.fixture(loop_scope="session")
async def tenant():
    name = f"doc_{uuid4().hex}"
    await apply_schema()
    yield name
    driver = await get_driver()
    async with driver.session() as session:
        await (await session.run("MATCH (n {tenant_id:$t}) DETACH DELETE n", t=name)).consume()


async def _seed(tenant):
    requester, _ = await _http_client(tenant, "requester", can_read_source=True)
    body = f"line one\n{SECRET}\nline three".encode()
    accepted = await requester.post(
        "/api/requests", data={"text": "First paragraph. Second sentence.\n\nNew paragraph."},
        files=[("files", ("notes.md", body, "text/markdown"))], headers={"Idempotency-Key": "doc"})
    assert accepted.status_code == 202, accepted.text
    rid = accepted.json()["request_id"]

    async def attachment(tx):
        row = await (await tx.run(
            "MATCH (a:Attachment {request_id:$id,tenant_id:$tenant}) RETURN a.id AS id", id=rid, tenant=tenant)).single()
        return row["id"]
    return requester, rid, await read_tx(tenant, attachment)


async def test_document_returns_ordered_units_with_text_for_source_reader(tenant):
    requester, rid, att = await _seed(tenant)
    try:
        response = await requester.get(f"/api/requests/{rid}/revisions/1/document", params={"source": att})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["can_read_source"] is True and body["revision"] == 1
        assert body["filename"] == "notes.md" and body["kind"] == "md"
        assert [u["location"]["line_start"] for u in body["units"]] == [1, 2, 3]
        assert [u["order"] for u in body["units"]] == [0, 1, 2]
        assert body["units"][1]["text"] == SECRET and body["units"][1]["unit_id"].startswith("esp_")
        chat = (await requester.get(f"/api/requests/{rid}/revisions/1/document", params={"source": "chat"})).json()
        assert chat["kind"] == "chat" and [u["location"]["paragraph"] for u in chat["units"]] == [0, 0, 1]
        by_id = await requester.get(f"/api/requests/{rid}/revisions/{body['revision_id']}/document", params={"source": att})
        assert by_id.status_code == 200
    finally:
        await requester.aclose()


async def test_document_hides_text_without_source_permission_and_other_tenant_404(tenant):
    requester, rid, att = await _seed(tenant)
    plain_operator, _ = await _http_client(tenant, "operator", can_read_source=False)
    source_operator, _ = await _http_client(tenant, "operator", can_read_source=True)
    outsider, _ = await _http_client(f"other_{uuid4().hex}", "operator", can_read_source=True)
    try:
        denied = await plain_operator.get(f"/api/requests/{rid}/revisions/1/document", params={"source": att})
        assert denied.status_code == 200
        assert denied.json()["can_read_source"] is False
        assert SECRET not in denied.text and "line one" not in denied.text
        assert all("text" not in u for u in denied.json()["units"])
        assert len(denied.json()["units"]) == 3  # positions/meta still shown
        chat = await plain_operator.get(f"/api/requests/{rid}/revisions/1/document", params={"source": "chat"})
        assert "First paragraph" not in chat.text
        assert SECRET in (await source_operator.get(f"/api/requests/{rid}/revisions/1/document", params={"source": att})).text
        assert (await outsider.get(f"/api/requests/{rid}/revisions/1/document", params={"source": att})).status_code == 404
        assert (await requester.get(f"/api/requests/{rid}/revisions/9/document", params={"source": att})).status_code == 404
        assert (await requester.get(f"/api/requests/{rid}/revisions/1/document", params={"source": "att_missing"})).status_code == 404
    finally:
        for client in (requester, plain_operator, source_operator, outsider):
            await client.aclose()


async def test_document_requires_view_scope_for_requester_role(tenant):
    requester, rid, att = await _seed(tenant)
    stranger, _ = await _http_client(tenant, "requester", can_read_source=True)  # other user, other org
    try:
        assert (await stranger.get(f"/api/requests/{rid}/revisions/1/document", params={"source": att})).status_code == 404
    finally:
        await requester.aclose()
        await stranger.aclose()


async def test_document_reviewer_matrix(tenant):
    requester, rid, att = await _seed(tenant)
    with_source, with_source_user = await _http_client(tenant, "reviewer", can_read_source=True)
    without_source, _ = await _http_client(tenant, "reviewer", can_read_source=True)
    no_flag, no_flag_user = await _http_client(tenant, "reviewer", can_read_source=False)
    driver = await get_driver()
    async with driver.session() as session:  # share the request with each reviewer's org
        await (await session.run(
            "MATCH (u:User {tenant_id:$tenant})-[:MEMBER_OF]->(o:Org) WHERE u.id IN $users "
            "WITH collect(o.id) AS orgs MATCH (r:Request {id:$rid,tenant_id:$tenant}) SET r.shared_org_ids=orgs",
            tenant=tenant, users=[with_source_user, no_flag_user], rid=rid)).consume()
    try:
        ok = await with_source.get(f"/api/requests/{rid}/revisions/1/document", params={"source": att})
        assert ok.status_code == 200 and SECRET in ok.text
        hidden = await no_flag.get(f"/api/requests/{rid}/revisions/1/document", params={"source": att})
        assert hidden.status_code == 200 and SECRET not in hidden.text
        assert hidden.json()["can_read_source"] is False and len(hidden.json()["units"]) == 3
        # a source-capable reviewer outside the request's orgs cannot even see the request
        assert (await without_source.get(f"/api/requests/{rid}/revisions/1/document", params={"source": att})).status_code == 404
    finally:
        for client in (requester, with_source, without_source, no_flag):
            await client.aclose()
