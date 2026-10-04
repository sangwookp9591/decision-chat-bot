"""Tenant-scoped managed Neo4j transactions."""

import logging
import os
import re
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import TypeVar

from neo4j import AsyncTransaction, unit_of_work

from jevtriage.config import get_settings
from jevtriage.db.driver import get_driver

T = TypeVar("T")
TxFunction = Callable[["TenantTx"], Awaitable[T]]
_after_commit: ContextVar[list[Callable[[], Awaitable[None]]] | None] = ContextVar("after_commit", default=None)
_logger = logging.getLogger(__name__)
after_commit_failures = 0
tenant_scope_warnings = 0
cross_tenant_transactions = 0
_TENANT_PARAMETERS = ("tenant_id", "tenant")
_TENANT_REFERENCE = re.compile(r"\$(?:tenant_id|tenant)\b")


class TenantTx:
    """Guard the tenant parameters on each Cypher statement in a transaction."""

    def __init__(self, tx: AsyncTransaction, tenant_id: str):
        self._tx = tx
        self.tenant_id = tenant_id

    async def run(self, query: str, **params):
        global tenant_scope_warnings
        for key in _TENANT_PARAMETERS:
            if key in params and params[key] != self.tenant_id:
                raise ValueError(f"{key} conflicts with transaction tenant_id")
        if not _TENANT_REFERENCE.search(query):
            if os.environ.get("JEVTRIAGE_STRICT_TENANT") == "1":
                raise ValueError("Cypher query lacks a tenant parameter")
            tenant_scope_warnings += 1
            _logger.warning("Cypher query lacks a tenant parameter", extra={"tenant_id": self.tenant_id})
        params["tenant_id"] = self.tenant_id
        if re.search(r"\$tenant\b", query):
            params["tenant"] = self.tenant_id
        return await self._tx.run(query, **params)


class _CrossTenantTx:
    """Explicitly unscoped transaction for operational cross-tenant work."""

    def __init__(self, tx: AsyncTransaction):
        self._tx = tx

    async def run(self, query: str, **params):
        return await self._tx.run(query, **params)


async def cross_tenant_tx(
    reason: str, fn: Callable[[_CrossTenantTx], Awaitable[T]], *,
    write: bool = False, timeout_seconds: float | None = None,
) -> T:
    """Run a schema/worker/retention query with an auditable reason."""
    if not reason or not reason.strip():
        raise ValueError("cross_tenant_tx requires a reason")
    global cross_tenant_transactions
    cross_tenant_transactions += 1
    _logger.info("Cross-tenant transaction", extra={"reason": reason})
    timeout = timeout_seconds if timeout_seconds is not None else (
        get_settings().neo4j_write_timeout_seconds if write else get_settings().neo4j_read_timeout_seconds
    )
    if timeout <= 0:
        raise ValueError("transaction timeout must be positive")
    driver = await get_driver()
    async with driver.session() as session:
        async def attempt(tx):
            return await fn(_CrossTenantTx(tx))

        work = unit_of_work(timeout=timeout)(attempt)
        if write:
            return await session.execute_write(work)
        return await session.execute_read(work)


def on_commit(callback: Callable[[], Awaitable[None]]) -> None:
    """Register a best-effort action for the current write attempt."""
    callbacks = _after_commit.get()
    if callbacks is None:
        raise RuntimeError("on_commit requires write_tx")
    callbacks.append(callback)


async def write_tx(tenant_id: str, fn: TxFunction[T], *, timeout_seconds: float | None = None) -> T:
    if not tenant_id:
        raise ValueError("tenant_id is required")
    timeout = timeout_seconds if timeout_seconds is not None else get_settings().neo4j_write_timeout_seconds
    if timeout <= 0:
        raise ValueError("transaction timeout must be positive")
    driver = await get_driver()
    async with driver.session() as session:
        committed_callbacks = []

        async def attempt(tx):
            nonlocal committed_callbacks
            callbacks = []
            token = _after_commit.set(callbacks)
            try:
                result = await fn(TenantTx(tx, tenant_id))
                committed_callbacks = callbacks
                return result
            finally:
                _after_commit.reset(token)

        result = await session.execute_write(unit_of_work(timeout=timeout)(attempt))
    global after_commit_failures
    for callback in committed_callbacks:
        try:
            await callback()
        except Exception:  # notification must not change committed result
            after_commit_failures += 1
            _logger.exception("Post-commit notification failed")
    return result


async def read_tx(tenant_id: str, fn: TxFunction[T], *, timeout_seconds: float | None = None) -> T:
    if not tenant_id:
        raise ValueError("tenant_id is required")
    timeout = timeout_seconds if timeout_seconds is not None else get_settings().neo4j_read_timeout_seconds
    if timeout <= 0:
        raise ValueError("transaction timeout must be positive")
    driver = await get_driver()
    async with driver.session() as session:
        async def attempt(tx):
            return await fn(TenantTx(tx, tenant_id))

        return await session.execute_read(unit_of_work(timeout=timeout)(attempt))


async def db_now_in_tx(tx: AsyncTransaction):
    result = await tx.run("RETURN $tenant_id AS tenant_id, datetime() AS now")
    return (await result.single(strict=True))["now"]


async def db_now(tenant_id: str):
    return await read_tx(tenant_id, db_now_in_tx)
