"""Redis client with graceful in-memory fallback (dev without Redis)."""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: Optional[redis.Redis] = None
_use_memory = False
_mem_store: dict[str, tuple[float, str]] = {}


def get_redis() -> redis.Redis | None:
    """Return a Redis client, or None if unavailable (callers use in-memory fallback)."""
    global _client, _use_memory
    if _client is not None:
        return _client
    try:
        _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=2)
        _client.ping()
        logger.info("Redis connected: %s", settings.REDIS_URL)
        return _client
    except Exception as exc:  # noqa: BLE001
        _use_memory = True
        logger.warning("Redis unavailable (%s). Using in-memory cache fallback.", exc)
        return None


class Cache:
    """Thin cache abstraction: Redis when available, in-memory dict otherwise."""

    def __init__(self, ttl: int = 300) -> None:
        self.ttl = ttl
        self._client = get_redis()

    def get(self, key: str) -> Optional[Any]:
        if self._client is not None:
            raw = self._client.get(key)
            return json.loads(raw) if raw else None
        item = _mem_store.get(key)
        if not item:
            return None
        exp, value = item
        if exp < time.time():
            _mem_store.pop(key, None)
            return None
        return json.loads(value)

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = ttl or self.ttl
        payload = json.dumps(value, default=str)
        if self._client is not None:
            self._client.setex(key, ttl, payload)
        else:
            _mem_store[key] = (time.time() + ttl, payload)

    def delete(self, key: str) -> None:
        if self._client is not None:
            self._client.delete(key)
        else:
            _mem_store.pop(key, None)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None


cache = Cache()
