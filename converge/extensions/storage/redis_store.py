"""
Redis-backed Store implementation.

Requires the redis package (pip install converge[store-backends]).
Uses pickle for serialization; implements atomic put_if_absent via SET NX.
Use SCAN for list(prefix) to avoid blocking in production.
"""
from __future__ import annotations

import pickle
from typing import TYPE_CHECKING, Any

from converge.core.store import Store

if TYPE_CHECKING:
    from redis import Redis

try:
    import redis
except ImportError:
    redis = None  # type: ignore[assignment]


class RedisStore(Store):
    """
    Redis-backed Store. Serialization uses pickle; values are stored as bytes.
    put_if_absent is atomic via SET key value NX. list(prefix) uses SCAN with
    match prefix* for production-safe iteration.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        *,
        client: Redis | None = None,
    ) -> None:
        if redis is None:
            raise ImportError(
                "redis is required for RedisStore. Install with: pip install converge[store-backends]",
            )
        if client is not None:
            self._client = client
        else:
            self._client = redis.from_url(redis_url, decode_responses=False)

    def put(self, key: str, value: Any) -> None:
        data = pickle.dumps(value)
        self._client.set(key, data)

    def get(self, key: str) -> Any | None:
        data = self._client.get(key)
        if data is None:
            return None
        if not isinstance(data, bytes):
            return None
        try:
            return pickle.loads(data)
        except Exception:
            return None

    def delete(self, key: str) -> None:
        self._client.delete(key)

    def list(self, prefix: str = "") -> list[str]:
        keys: list[str] = []
        for k in self._client.scan_iter(match=prefix + "*"):
            if isinstance(k, bytes):
                keys.append(k.decode("utf-8", errors="replace"))
            else:
                keys.append(k)
        return keys

    def put_if_absent(self, key: str, value: Any) -> bool:
        data = pickle.dumps(value)
        result = self._client.set(key, data, nx=True)
        return result is True
