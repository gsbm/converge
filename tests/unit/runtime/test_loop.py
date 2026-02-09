"""Tests for converge.runtime.loop."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from converge.coordination.pool_manager import PoolManager
from converge.core.agent import Agent
from converge.core.identity import Identity
from converge.core.message import Message
from converge.network.transport.local import LocalTransport
from converge.runtime.loop import AgentRuntime, Inbox


@pytest.mark.asyncio
async def test_inbox_drop_when_full():
    inbox = Inbox(maxsize=1, drop_when_full=True)
    await inbox.push(1)
    await inbox.push(2)
    batch = inbox.poll(batch_size=10)
    assert len(batch) == 1
    assert batch[0] == 1


class CoverageAgent(Agent):
    def __init__(self, identity):
        super().__init__(identity=identity)
        self.decisions_to_make = []

    def decide(self, messages, tasks):
        if self.decisions_to_make:
            return self.decisions_to_make.pop(0)
        return []


@pytest.mark.asyncio
async def test_runtime_stops_cleanly():
    id_a = Identity.generate()
    agent = CoverageAgent(id_a)
    transport = LocalTransport(id_a.fingerprint)
    runtime = AgentRuntime(agent, transport)

    await runtime.start()
    await asyncio.sleep(0.01)
    await runtime.stop()
    assert not runtime.running


@pytest.mark.asyncio
async def test_runtime_executes_decisions():
    id_a = Identity.generate()
    agent = CoverageAgent(id_a)
    transport = LocalTransport(id_a.fingerprint)
    runtime = AgentRuntime(agent, transport)

    msg = Message(sender=id_a.fingerprint, payload={"test": "data"})
    agent.decisions_to_make.append([msg])

    await runtime.start()

    await runtime.inbox.push(Message(sender="sys", payload="tick"))
    runtime.scheduler.notify()
    await asyncio.sleep(0.05)

    await runtime.stop()


@pytest.mark.asyncio
async def test_runtime_exception_handling():
    from converge.core.decisions import JoinPool

    id_a = Identity.generate()

    class ErrorAgent(Agent):
        def decide(self, m, t):
            return [JoinPool("p1")]

    agent = ErrorAgent(id_a)
    transport = LocalTransport(id_a.fingerprint)

    pm = PoolManager()

    def raiser(*args):
        raise ValueError("Boom")

    pm.join_pool = raiser

    runtime = AgentRuntime(agent, transport, pool_manager=pm)
    await runtime.start()

    await runtime.inbox.push(Message(sender="sys", payload="tick"))
    runtime.scheduler.notify()
    await asyncio.sleep(0.05)

    await runtime.stop()


@pytest.mark.asyncio
async def test_runtime_double_start():
    id_a = Identity.generate()
    agent = CoverageAgent(id_a)
    transport = LocalTransport(id_a.fingerprint)
    runtime = AgentRuntime(agent, transport)

    await runtime.start()
    await runtime.start()
    assert runtime.running
    await runtime.stop()


@pytest.mark.asyncio
async def test_inbox_poll_limit():
    inbox = Inbox()
    for i in range(15):
        await inbox.push(i)

    batch = inbox.poll()
    assert len(batch) == 10

    batch2 = inbox.poll()
    assert len(batch2) == 5


@pytest.mark.asyncio
async def test_runtime_listen_error():
    identity = Identity.generate()
    agent = Agent(identity)
    transport = MagicMock()
    transport.receive.side_effect = [Exception("Transport error"), asyncio.CancelledError()]
    transport.start = AsyncMock(return_value=None)
    transport.stop = AsyncMock(return_value=None)

    runtime = AgentRuntime(agent, transport)
    await runtime.start()
    await asyncio.sleep(1.2)
    await runtime.stop()


@pytest.mark.asyncio
async def test_runtime_stop_before_start():
    identity = Identity.generate()
    agent = Agent(identity)
    transport = LocalTransport(identity.fingerprint)
    runtime = AgentRuntime(agent, transport)
    await runtime.stop()
    assert not runtime.running


@pytest.mark.asyncio
async def test_runtime_listen_cancelled_break():
    identity = Identity.generate()
    agent = Agent(identity)
    transport = MagicMock()
    transport.receive.return_value = asyncio.get_event_loop().create_future()
    transport.start = AsyncMock(return_value=None)
    transport.stop = AsyncMock(return_value=None)
    runtime = AgentRuntime(agent, transport)
    await runtime.start()
    await asyncio.sleep(0.05)
    await runtime.stop()


@pytest.mark.asyncio
async def test_runtime_stop_without_scheduler():
    identity = Identity.generate()
    agent = Agent(identity)
    transport = LocalTransport(identity.fingerprint)
    runtime = AgentRuntime(agent, transport)
    await runtime.start()
    del runtime.scheduler
    await runtime.stop()
    assert not runtime.running


@pytest.mark.asyncio
async def test_runtime_wait_for_work_timeout():
    identity = Identity.generate()
    agent = Agent(identity)
    transport = LocalTransport(identity.fingerprint)
    runtime = AgentRuntime(agent, transport)
    await runtime.start()
    await asyncio.sleep(1.2)
    await runtime.stop()
    assert not runtime.running


@pytest.mark.asyncio
async def test_runtime_coverage_edges():
    identity = Identity.generate()
    agent = Agent(identity)
    transport = LocalTransport(identity.fingerprint)
    runtime = AgentRuntime(agent, transport)

    await runtime.start()
    await runtime.stop()

    msg = Message(sender=identity.fingerprint)
    await runtime.transport.start()
    await runtime._execute_decision_fallback(msg)
    signed = msg.sign(identity)
    await runtime._execute_decision_fallback(signed)
    await runtime.transport.stop()


@pytest.mark.asyncio
async def test_runtime_metrics_and_hooks():
    from converge.observability.metrics import MetricsCollector

    class HookAgent(Agent):
        def __init__(self, identity):
            super().__init__(identity)
            self.started = False
            self.stopped = False
            self.ticks = 0

        def on_start(self):
            self.started = True

        def on_stop(self):
            self.stopped = True

        def on_tick(self, messages, tasks):
            self.ticks += 1

    identity = Identity.generate()
    agent = HookAgent(identity)
    transport = LocalTransport(identity.fingerprint)
    metrics = MetricsCollector()
    runtime = AgentRuntime(agent, transport, metrics_collector=metrics)
    await runtime.start()
    assert agent.started
    await transport.send(Message(sender="other", recipient=identity.fingerprint, payload={}))
    await asyncio.sleep(0.3)
    await runtime.stop()
    assert agent.stopped
    assert agent.ticks >= 1
    assert metrics.snapshot()["counters"].get("messages_received", 0) >= 1


@pytest.mark.asyncio
async def test_runtime_agent_decide_coroutine():
    """Runtime handles agent.decide as async (inspect.iscoroutinefunction)."""
    identity = Identity.generate()

    class AsyncDecideAgent(Agent):
        async def decide(self, messages, tasks):
            return []

    agent = AsyncDecideAgent(identity)
    transport = LocalTransport(identity.fingerprint)
    runtime = AgentRuntime(agent, transport)
    await runtime.start()
    await asyncio.sleep(0.05)
    await runtime.stop()
    assert not runtime.running


@pytest.mark.asyncio
async def test_execute_decision_fallback_non_message():
    """_execute_decision_fallback with decision that has no 'sender' (not a Message) does not crash."""
    identity = Identity.generate()
    agent = Agent(identity)
    transport = LocalTransport(identity.fingerprint)
    runtime = AgentRuntime(agent, transport)
    await runtime.start()
    class NotAMessage:
        pass
    await runtime._execute_decision_fallback(NotAMessage())
    await runtime.stop()


@pytest.mark.asyncio
async def test_runtime_no_managers_uses_fallback():
    """When task_manager and pool_manager are None, executor is None and fallback is used (covers line 189)."""
    identity = Identity.generate()
    msg = Message(sender=identity.fingerprint, payload={"x": 1})

    class DecideAgent(Agent):
        def decide(self, messages, tasks):
            return [msg]

    agent = DecideAgent(identity)
    transport = LocalTransport(identity.fingerprint)
    runtime = AgentRuntime(agent, transport, pool_manager=None, task_manager=None)
    await runtime.start()
    await runtime.inbox.push(Message(sender="other", payload="tick"))
    runtime.scheduler.notify()
    await asyncio.sleep(0.2)
    await runtime.stop()
