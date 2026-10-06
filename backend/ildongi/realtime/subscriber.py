"""Per-tenant Redis listener; every wake-up causes a Neo4j cursor replay."""

import asyncio
import logging

from redis.asyncio import Redis

from ildongi.config import get_settings

_log = logging.getLogger(__name__)


class TenantSubscriber:
    def __init__(self, tenant_id: str, redis_url: str | None = None):
        self.tenant_id = tenant_id
        self.channel = f"tenant:{tenant_id}"
        self.redis_url = redis_url or get_settings().redis_url
        self.connected = False
        self._wake = asyncio.Event()
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self.redis_url and self._task is None:
            self._task = asyncio.create_task(self._listen())

    async def _listen(self) -> None:
        while True:
            client = Redis.from_url(self.redis_url, socket_connect_timeout=0.25, socket_timeout=1)
            pubsub = client.pubsub()
            try:
                await pubsub.subscribe(self.channel)
                self.connected = True
                self._wake.set()  # replay events committed before subscription
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        self._wake.set()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - retry while hub uses normal polling
                _log.exception("Redis subscriber disconnected for tenant %s", self.tenant_id)
            finally:
                self.connected = False
                self._wake.set()
                await pubsub.aclose()
                await client.aclose()
            await asyncio.sleep(1)

    async def wait(self, timeout: float | None = None) -> None:
        try:
            await asyncio.wait_for(self._wake.wait(), timeout)
        finally:
            self._wake.clear()

    async def close(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None


class JobSubscriber(TenantSubscriber):
    """Optional worker wake-up; Job discovery still handles missed messages."""

    def __init__(self, redis_url: str | None = None):
        super().__init__("jobs", redis_url)
        self.channel = "jobs"
