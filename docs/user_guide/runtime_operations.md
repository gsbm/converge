# Runtime operations: hooks, rate limiting, ops server, and replay

This guide shows a production composition pattern using:

- `HookedTransport` for reusable message middleware,
- `RateLimitHook` for ingress/egress control,
- `RuntimeOpsServer` for `/health`, `/ready`, `/metrics`,
- `ReplayLog` + `ReplayRunner` for audit and deterministic replay.

## Recommended production shape

1. Build your base transport (`LocalTransport`, `TcpTransport`, or custom).
2. Wrap it with `HookedTransport` and register middleware hooks in deterministic order.
3. Add `RateLimitHook` as one of those hooks (usually early in chain).
4. Pass `ReplayLog` and `MetricsCollector` into `AgentRuntime`.
5. Create `RuntimeOpsServer(runtime, metrics, host, port)` and pass it as `ops_server`.
6. Enable `identity_registry` so unverified messages are dropped on verified receive paths.

## End-to-end composition example

```python
import asyncio

from converge.core.agent import Agent
from converge.core.identity import Identity
from converge.coordination.pool_manager import PoolManager
from converge.coordination.task_manager import TaskManager
from converge.extensions.rate_limit import RateLimitHook, RateLimiter, TokenBucketConfig
from converge.network.transport.hooks import HookedTransport
from converge.network.transport.tcp import TcpTransport
from converge.observability.metrics import MetricsCollector
from converge.observability.replay import ReplayLog
from converge.observability.runtime_ops import RuntimeOpsServer
from converge.runtime.loop import AgentRuntime


class MyAgent(Agent):
    def decide(self, messages, tasks):
        return []


async def main():
    identity = Identity.generate()
    agent = MyAgent(identity)

    base_transport = TcpTransport(host="0.0.0.0", port=9001, agent_id=agent.id)

    limiter = RateLimiter(
        global_config=TokenBucketConfig(capacity=200, refill_tokens_per_sec=100),
        sender_config=TokenBucketConfig(capacity=60, refill_tokens_per_sec=20),
        topic_config=TokenBucketConfig(capacity=120, refill_tokens_per_sec=40),
    )

    metrics = MetricsCollector()
    transport = HookedTransport(
        base_transport,
        hooks=[
            RateLimitHook(limiter, metrics_collector=metrics),
            # add custom MessageHook implementations here
        ],
    )

    replay_log = ReplayLog()
    pool_manager = PoolManager()
    task_manager = TaskManager()

    runtime = AgentRuntime(
        agent=agent,
        transport=transport,
        pool_manager=pool_manager,
        task_manager=task_manager,
        metrics_collector=metrics,
        replay_log=replay_log,
        health_check=lambda: True,
        ready_check=lambda: True,
    )

    ops_server = RuntimeOpsServer(runtime, metrics, host="127.0.0.1", port=9100)
    runtime.ops_server = ops_server

    await runtime.start()
    try:
        await asyncio.sleep(60)
    finally:
        await runtime.stop()


asyncio.run(main())
```

## Hook ordering and failure behavior

- `pre_send` hooks execute in registration order.
- `post_receive` hooks execute in registration order.
- Returning `None` drops the message.
- Hook exceptions trigger `on_error(stage, error, context)` when provided.

Suggested order:

1. lightweight validation,
2. rate limiting,
3. normalization/enrichment,
4. policy enforcement.

## Rate limiting guidance

- Use global + sender + topic buckets together for defense in depth.
- Prefer a shared store-backed limiter when you run multiple processes.
- Monitor:
  - `rate_limit_ingress_dropped_total`
  - `rate_limit_egress_dropped_total`

## Ops server guidance

`RuntimeOpsServer` exposes:

- `GET /health` -> runtime health (`200` or `503`)
- `GET /ready` -> runtime readiness (`200` or `503`)
- `GET /metrics` -> Prometheus text from `MetricsCollector`

Typical deployment:

- bind to loopback (`127.0.0.1`) or a private interface,
- front with your platform ingress (TLS, authn/authz),
- scrape `/metrics` with Prometheus and alert on drops/failures.

## Replay workflows in production

Use replay for post-incident analysis, deterministic simulations, and regression checks.

```python
import asyncio
from converge.observability.replay import ReplayRunner


async def replay_example(replay_log):
    runner = ReplayRunner(replay_log)

    # 1) Plan-only dry run
    plan = await runner.replay(
        direction="inbound",
        agent_id="agent-123",
        dry_run=True,
    )
    print(f"events planned: {len(plan)}")

    # 2) Execute into callback in timestamp order
    async def sink(message):
        # inject into a mock transport, validator, or test harness
        pass

    await runner.replay(direction="inbound", callback=sink)


asyncio.run(replay_example(replay_log))
```

Practical replay policy:

1. Keep replay logs immutable after export.
2. Filter by `agent_id` and `direction` for targeted incident replay.
3. Replay into non-production paths first (`dry_run` + callback harness).
4. Document dedupe/idempotency expectations for anything that can trigger side effects.
