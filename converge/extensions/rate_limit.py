from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from converge.core.message import Message
from converge.core.store import Store
from converge.extensions.storage.memory import MemoryStore
from converge.network.transport.hooks import MessageHook
from converge.observability.metrics import MetricsCollector


@dataclass(frozen=True)
class TokenBucketConfig:
    capacity: float
    refill_tokens_per_sec: float


class RateLimiter:
    def __init__(
        self,
        *,
        store: Store | None = None,
        global_config: TokenBucketConfig | None = None,
        sender_config: TokenBucketConfig | None = None,
        topic_config: TokenBucketConfig | None = None,
    ) -> None:
        self.store = store or MemoryStore()
        self.global_config = global_config
        self.sender_config = sender_config
        self.topic_config = topic_config

    def allow_message(self, message: Message, *, direction: str) -> bool:
        checks: list[tuple[str, TokenBucketConfig]] = []
        if self.global_config is not None:
            checks.append((f"{direction}:global", self.global_config))
        if self.sender_config is not None and message.sender:
            checks.append((f"{direction}:sender:{message.sender}", self.sender_config))
        if self.topic_config is not None:
            for topic in message.topics:
                checks.append((f"{direction}:topic:{topic.namespace}", self.topic_config))
        return all(self._consume(key, cfg) for key, cfg in checks)

    def _consume(self, key: str, cfg: TokenBucketConfig) -> bool:
        now = time.monotonic()
        state_key = f"rate_limit:{key}"
        state = self.store.get(state_key)
        if not isinstance(state, dict):
            tokens = cfg.capacity
            last_ts = now
        else:
            tokens = float(state.get("tokens", cfg.capacity))
            last_ts = float(state.get("last_ts", now))
        elapsed = max(0.0, now - last_ts)
        replenished = min(cfg.capacity, tokens + (elapsed * cfg.refill_tokens_per_sec))
        if replenished < 1.0:
            self.store.put(state_key, {"tokens": replenished, "last_ts": now})
            return False
        self.store.put(state_key, {"tokens": replenished - 1.0, "last_ts": now})
        return True


class RateLimitHook(MessageHook):
    def __init__(
        self,
        rate_limiter: RateLimiter,
        *,
        metrics_collector: MetricsCollector | None = None,
    ) -> None:
        self.rate_limiter = rate_limiter
        self.metrics = metrics_collector

    def pre_send(self, message: Message) -> Message | None:
        if self.rate_limiter.allow_message(message, direction="egress"):
            return message
        if self.metrics:
            self.metrics.inc("rate_limit_egress_dropped_total")
        return None

    def post_receive(self, message: Message) -> Message | None:
        if self.rate_limiter.allow_message(message, direction="ingress"):
            return message
        if self.metrics:
            self.metrics.inc("rate_limit_ingress_dropped_total")
        return None

    def on_error(self, stage: str, error: Exception, context: dict[str, Any]) -> None:
        _ = (stage, error, context)
