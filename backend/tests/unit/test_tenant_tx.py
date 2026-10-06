"""Tenant transaction boundary regression tests."""

from unittest.mock import AsyncMock

import pytest

from ildongi.db import tx as tx_module
from ildongi.db.tx import TenantTx, cross_tenant_tx


@pytest.mark.asyncio
async def test_tenant_parameter_is_injected(monkeypatch):
    monkeypatch.setenv("ILDONGI_STRICT_TENANT", "1")
    raw = AsyncMock()
    tx = TenantTx(raw, "tenant-a")
    await tx.run("MATCH (n {tenant_id:$tenant_id}) RETURN n", limit=1)
    raw.run.assert_awaited_once_with(
        "MATCH (n {tenant_id:$tenant_id}) RETURN n", limit=1, tenant_id="tenant-a",
    )


@pytest.mark.asyncio
async def test_conflicting_tenant_parameter_fails(monkeypatch):
    monkeypatch.setenv("ILDONGI_STRICT_TENANT", "1")
    tx = TenantTx(AsyncMock(), "tenant-a")
    with pytest.raises(ValueError, match="tenant_id"):
        await tx.run("MATCH (n {tenant_id:$tenant_id}) RETURN n", tenant_id="tenant-b")


@pytest.mark.asyncio
async def test_registered_alias_is_injected_and_checked(monkeypatch):
    monkeypatch.setenv("ILDONGI_STRICT_TENANT", "1")
    raw = AsyncMock()
    tx = TenantTx(raw, "tenant-a")
    await tx.run("MATCH (n {tenant_id:$tenant}) RETURN n")
    assert raw.run.await_args.kwargs["tenant"] == "tenant-a"
    with pytest.raises(ValueError, match="tenant"):
        await tx.run("MATCH (n {tenant_id:$tenant}) RETURN n", tenant="tenant-b")


@pytest.mark.asyncio
async def test_unscoped_query_fails_in_strict_mode(monkeypatch):
    monkeypatch.setenv("ILDONGI_STRICT_TENANT", "1")
    tx = TenantTx(AsyncMock(), "tenant-a")
    with pytest.raises(ValueError, match="tenant"):
        await tx.run("MATCH (n) RETURN n")


@pytest.mark.asyncio
async def test_unscoped_query_warns_in_operating_mode(monkeypatch, caplog):
    monkeypatch.delenv("ILDONGI_STRICT_TENANT", raising=False)
    raw = AsyncMock()
    before = tx_module.tenant_scope_warnings
    await TenantTx(raw, "tenant-a").run("MATCH (n) RETURN n")
    assert tx_module.tenant_scope_warnings == before + 1
    assert "lacks a tenant parameter" in caplog.text


@pytest.mark.asyncio
async def test_cross_tenant_requires_reason(monkeypatch):
    monkeypatch.setenv("ILDONGI_STRICT_TENANT", "1")
    with pytest.raises(ValueError, match="reason"):
        await cross_tenant_tx("", lambda tx: tx.run("MATCH (n) RETURN n"))
