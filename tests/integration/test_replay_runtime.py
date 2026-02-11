"""Integration tests for ReplayLog with AgentRuntime."""

import asyncio

from converge.coordination.pool_manager import PoolManager
from converge.coordination.task_manager import TaskManager
from converge.core.agent import Agent
from converge.core.identity import Identity
from converge.core.message import Message
from converge.extensions.storage.memory import MemoryStore
from converge.network.transport.local import LocalTransport, LocalTransportRegistry
from converge.observability.replay import ReplayLog
from converge.runtime.loop import AgentRuntime


async def test_runtime_replay_log_records_incoming():
    """Run runtime with ReplayLog; inject one message; assert it is recorded."""
    registry = LocalTransportRegistry()
    registry.clear()

    identity = Identity.generate()
    agent = Agent(identity)
    transport = LocalTransport(agent.id)
    replay_log = ReplayLog()
    pool_manager = PoolManager(store=MemoryStore())
    task_manager = TaskManager(store=MemoryStore())

    runtime = AgentRuntime(
        agent=agent,
        transport=transport,
        pool_manager=pool_manager,
        task_manager=task_manager,
        replay_log=replay_log,
    )

    async def run_and_inject():
        await runtime.start()
        # Inject one message into this agent's queue so _listen_transport receives it
        queue = registry.get_queue(agent.id)
        assert queue is not None
        msg = Message(sender="other", recipient=agent.id, payload={"test": 1})
        await queue.put(msg)
        await asyncio.sleep(0.3)
        await runtime.stop()

    await run_and_inject()

    assert len(replay_log.events) >= 1
    assert replay_log.events[0]["type"] == "message"
    assert replay_log.events[0]["data"]["sender"] == "other"
