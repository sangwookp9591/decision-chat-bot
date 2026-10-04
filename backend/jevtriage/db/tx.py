"""Tenant-scoped managed Neo4j transactions."""

import logging
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import TypeVar

from neo4j import AsyncTransaction, unit_of_work

from jevtriage.config import get_settings
from jevtriage.db.driver import get_driver

T = TypeVar("T")
TxFunction = Callable[[AsyncTransaction], Awaitable[T]]
_after_commit: ContextVar[list[Callable[[], Awaitable[None]]] | None] = ContextVar("after_commit", default=None)
_logger = logging.getLogger(__name__)
after_commit_failures = 0


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
                result = await fn(tx)
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
        return await session.execute_read(unit_of_work(timeout=timeout)(fn))


async def db_now_in_tx(tx: AsyncTransaction):
    result = await tx.run("RETURN datetime() AS now")
    return (await result.single(strict=True))["now"]


async def db_now(tenant_id: str):
    return await read_tx(tenant_id, db_now_in_tx)
