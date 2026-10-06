"""Best-effort Redis notifications and expiring global SSE slots."""

import asyncio
import logging
import time
from uuid import uuid4

from redis.asyncio import Redis

from ildongi.config import get_settings

_log = logging.getLogger(__name__)
publish_failures = 0


async def _publish(channel: str, value: str, redis_url: str | None = None) -> bool:
    global publish_failures
    url = redis_url or get_settings().redis_url
    if not url:
        return False
    client = Redis.from_url(url, socket_connect_timeout=0.25, socket_timeout=0.25)
    try:
        await client.publish(channel, value)
        return True
    except Exception:  # noqa: BLE001 - Neo4j commit has already succeeded
        publish_failures += 1
        _log.exception("Redis publish failed on %s", channel)
        return False
    finally:
        await client.aclose()


async def publish_event(tenant_id: str, seq: int, redis_url: str | None = None) -> bool:
    return await _publish(f"tenant:{tenant_id}", str(seq), redis_url)


async def publish_job(job_id: str, redis_url: str | None = None) -> bool:
    """Wake workers after a Job commit; Job discovery remains authoritative."""
    return await _publish("jobs", job_id, redis_url)


_ACQUIRE = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[2]) then return 0 end
redis.call('ZADD', KEYS[1], ARGV[3], ARGV[4])
redis.call('EXPIRE', KEYS[1], ARGV[5])
return 1
"""


class ConnectionSlots:
    """Global limit while Redis works; process-local limit during an outage."""

    def __init__(self, redis_url: str | None = None, limit: int = 100, ttl: int = 30):
        self.redis_url = redis_url or get_settings().redis_url
        self.limit = limit
        self.ttl = ttl
        self._local: set[str] = set()
        self._lock = asyncio.Lock()

    def _client(self) -> Redis:
        return Redis.from_url(self.redis_url, socket_connect_timeout=0.25, socket_timeout=0.25)

    async def acquire(self) -> str | None:
        token = uuid4().hex
        if self.redis_url:
            client = self._client()
            try:
                now = time.time()
                accepted = await client.eval(_ACQUIRE, 1, "sse:connections", now, self.limit,
                                             now + self.ttl, token, self.ttl * 2)
                return token if accepted else None
            except Exception:  # noqa: BLE001 - local fallback
                _log.exception("Redis connection limit unavailable; using local limit")
            finally:
                await client.aclose()
        async with self._lock:
            if len(self._local) >= self.limit:
                return None
            self._local.add(token)
            return f"local:{token}"

    async def refresh(self, token: str) -> None:
        if token.startswith("local:") or not self.redis_url:
            return
        client = self._client()
        try:
            await client.zadd("sse:connections", {token: time.time() + self.ttl}, xx=True)
            await client.expire("sse:connections", self.ttl * 2)
        except Exception:  # noqa: BLE001 - expiration prevents leaks
            _log.exception("Redis connection slot refresh failed")
        finally:
            await client.aclose()

    async def release(self, token: str) -> None:
        if token.startswith("local:"):
            async with self._lock:
                self._local.discard(token[6:])
        elif self.redis_url:
            client = self._client()
            try:
                await client.zrem("sse:connections", token)
            except Exception:  # noqa: BLE001 - TTL clears abandoned slot
                _log.exception("Redis connection slot release failed")
            finally:
                await client.aclose()
