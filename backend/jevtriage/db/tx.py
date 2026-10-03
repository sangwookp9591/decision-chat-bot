"""Tenant-scoped managed Neo4j transactions."""

from collections.abc import Awaitable, Callable
from typing import TypeVar

from neo4j import AsyncTransaction

from jevtriage.db.driver import get_driver

T = TypeVar("T")
TxFunction = Callable[[AsyncTransaction], Awaitable[T]]


async def write_tx(tenant_id: str, fn: TxFunction[T]) -> T:
    if not tenant_id:
        raise ValueError("tenant_id is required")
    driver = await get_driver()
    async with driver.session() as session:
        return await session.execute_write(fn)


async def read_tx(tenant_id: str, fn: TxFunction[T]) -> T:
    if not tenant_id:
        raise ValueError("tenant_id is required")
    driver = await get_driver()
    async with driver.session() as session:
        return await session.execute_read(fn)


async def db_now_in_tx(tx: AsyncTransaction):
    result = await tx.run("RETURN datetime() AS now")
    return (await result.single(strict=True))["now"]


async def db_now(tenant_id: str):
    return await read_tx(tenant_id, db_now_in_tx)
