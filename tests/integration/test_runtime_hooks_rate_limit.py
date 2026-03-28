"""Integration tests for runtime + transport hooks + rate limiting."""

import asyncio

from converge.coordination.pool_manager import PoolManager
from converge.coordination.task_manager import TaskManager
from converge.core.agent import Agent
from converge.core.identity import Identity
from converge.core.message import Message
from converge.extensions.rate_limit import RateLimiter, RateLimitHook, TokenBucketConfig
from converge.extensions.storage.memory import MemoryStore
from converge.network.transport.hooks import HookedTransport
from converge.network.transport.local import LocalTransport, LocalTransportRegistry
from converge.observability.metrics import MetricsCollector
from converge.runtime.loop import AgentRuntime


async def test_runtime_with_hooked_transport_ingress_rate_drop():
    registry = LocalTransportRegistry()
    registry.clear()

    sender_id = Identity.generate()
    receiver_id = Identity.generate()
    sender_transport = LocalTransport(sender_id.fingerprint)
    receiver_base = LocalTransport(receiver_id.fingerprint)
    metrics = MetricsCollector()
    limiter = RateLimiter(global_config=TokenBucketConfig(capacity=0.0, refill_tokens_per_sec=0.0))
    receiver_transport = HookedTransport(
        receiver_base,
        hooks=[RateLimitHook(limiter, metrics_collector=metrics)],
    )

    receiver_runtime = AgentRuntime(
        agent=Agent(receiver_id),
        transport=receiver_transport,
        pool_manager=PoolManager(store=MemoryStore()),
        task_manager=TaskManager(store=MemoryStore()),
        metrics_collector=metrics,
        receive_timeout_sec=0.05,
    )

    await sender_transport.start()
    await receiver_runtime.start()
    try:
        await sender_transport.send(
            Message(
                sender=sender_id.fingerprint,
                recipient=receiver_id.fingerprint,
                payload={"x": 1},
            ),
        )
        await asyncio.sleep(0.2)
        assert receiver_runtime.inbox.poll() == []
        assert metrics.snapshot()["counters"].get("rate_limit_ingress_dropped_total", 0) >= 1
    finally:
        await receiver_runtime.stop()
        await sender_transport.stop()
