import asyncio
from weakref import WeakKeyDictionary

from neo4j import AsyncDriver, AsyncGraphDatabase

from ildongi.config import Settings, get_settings

_drivers: WeakKeyDictionary[asyncio.AbstractEventLoop, AsyncDriver] = WeakKeyDictionary()


def create_driver(settings: Settings) -> AsyncDriver:
    """Create a Neo4j driver for readiness checks and application use."""
    return AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
        connection_timeout=settings.neo4j_connection_timeout_seconds,
        connection_acquisition_timeout=settings.neo4j_connection_acquisition_timeout_seconds,
        max_transaction_retry_time=settings.neo4j_transaction_retry_seconds,
    )


async def get_driver() -> AsyncDriver:
    loop = asyncio.get_running_loop()
    driver = _drivers.get(loop)
    if driver is None:
        driver = create_driver(get_settings())
        _drivers[loop] = driver
    return driver


async def close_driver() -> None:
    driver = _drivers.pop(asyncio.get_running_loop(), None)
    if driver is not None:
        await driver.close()
