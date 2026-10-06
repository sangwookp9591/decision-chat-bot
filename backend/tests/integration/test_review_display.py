"""Review list/detail expose the stored masked request title; preview follows source permission."""
from __future__ import annotations

import httpx
import pytest

from ildongi.auth.core import Principal, get_principal
from ildongi.db.tx import write_tx
from ildongi.main import create_app

from .test_review_assignment import sample, tenant  # noqa: F401

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _label(tenant_id: str, command: dict) -> None:
    async def op(tx):
        await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant,id:$id}) SET q.title='회의실 예약 자동화',q.preview='회의실 예약 자동화를 요청합니다. 상세…'",
            tenant=tenant_id, id=command["request_id"])).consume()
    await write_tx(tenant_id, op)


async def _list(app, principal):
    app.dependency_overrides[get_principal] = lambda: principal
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return (await client.get("/api/reviews?status=pending")).json()["reviews"]


async def test_review_list_carries_title_and_gates_preview(tenant):  # noqa: F811
    principal, review_id, command = await sample(tenant)
    await _label(tenant, command)
    app = create_app()
    allowed, principal = principal, Principal(
        principal.tenant_id, principal.user_id, principal.org_ids, principal.roles, False)
    row = next(r for r in await _list(app, principal) if r["id"] == review_id)
    assert row["title"] == "회의실 예약 자동화"
    assert "preview" not in row  # reviewer without source permission
    row = next(r for r in await _list(app, allowed) if r["id"] == review_id)
    assert row["preview"].startswith("회의실 예약")


async def test_review_detail_keeps_title_without_source_permission(tenant):  # noqa: F811
    principal, review_id, command = await sample(tenant)
    await _label(tenant, command)
    principal = Principal(principal.tenant_id, principal.user_id, principal.org_ids, principal.roles, False)
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: principal
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get(f"/api/reviews/{review_id}")).json()
    assert body["request"]["title"] == "회의실 예약 자동화"
    assert "preview" not in body["request"]
    assert "request_text" not in body["request"]


async def test_review_detail_includes_original_for_source_reader(tenant):  # noqa: F811
    principal, review_id, command = await sample(tenant)
    await _label(tenant, command)
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: principal
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get(f"/api/reviews/{review_id}")).json()
    assert body["request"]["request_text"] == "업무 판단 요청"
