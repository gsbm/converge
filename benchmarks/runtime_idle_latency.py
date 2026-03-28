#!/usr/bin/env python3
"""
Baseline benchmark for runtime idle CPU ratio and scheduler wake latency.

Run:
  .venv/bin/python benchmarks/runtime_idle_latency.py
Optional env:
  IDLE_SEC=3.0
  WAKE_ROUNDS=20
"""

import asyncio
import os
import statistics
import time

from converge.core.agent import Agent
from converge.core.identity import Identity
from converge.core.message import Message
from converge.network.transport.local import LocalTransport
from converge.runtime.loop import AgentRuntime

IDLE_SEC = float(os.environ.get("IDLE_SEC", "3.0"))
WAKE_ROUNDS = int(os.environ.get("WAKE_ROUNDS", "20"))


class _ProbeAgent(Agent):
    def __init__(self, identity):
        super().__init__(identity)
        self.tick_event = asyncio.Event()

    def decide(self, messages, tasks):
        if messages or tasks:
            self.tick_event.set()
        return []


async def _main() -> None:
    identity = Identity.generate()
    agent = _ProbeAgent(identity)
    runtime = AgentRuntime(
        agent=agent,
        transport=LocalTransport(agent.id),
        scheduler_timeout_sec=0.1,
    )
    await runtime.start()
    try:
        cpu_start = time.process_time()
        wall_start = time.perf_counter()
        await asyncio.sleep(IDLE_SEC)
        cpu_delta = time.process_time() - cpu_start
        wall_delta = time.perf_counter() - wall_start
        idle_cpu_ratio = cpu_delta / max(wall_delta, 1e-9)

        latencies_ms: list[float] = []
        for _ in range(WAKE_ROUNDS):
            agent.tick_event.clear()
            t0 = time.perf_counter()
            await runtime.inbox.push(Message(sender="probe", payload={"ping": True}))
            runtime.scheduler.notify()
            await asyncio.wait_for(agent.tick_event.wait(), timeout=1.0)
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)

        print(f"idle_seconds={IDLE_SEC:.2f}")
        print(f"idle_cpu_ratio={idle_cpu_ratio:.6f}")
        print(f"wake_rounds={WAKE_ROUNDS}")
        print(f"wake_latency_ms_min={min(latencies_ms):.3f}")
        print(f"wake_latency_ms_p50={statistics.median(latencies_ms):.3f}")
        print(f"wake_latency_ms_p95={statistics.quantiles(latencies_ms, n=20)[18]:.3f}")
        print(f"wake_latency_ms_max={max(latencies_ms):.3f}")
    finally:
        await runtime.stop()


if __name__ == "__main__":
    asyncio.run(_main())
