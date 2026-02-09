"""Tests for converge.runtime.executor."""

from unittest.mock import MagicMock

import pytest

from converge.coordination.pool_manager import PoolManager
from converge.coordination.task_manager import TaskManager
from converge.core.decisions import (
    ClaimTask,
    CreatePool,
    JoinPool,
    LeavePool,
    ReportTask,
    SendMessage,
    SubmitTask,
)
from converge.core.identity import Identity
from converge.core.message import Message
from converge.core.task import Task
from converge.runtime.executor import Executor, StandardExecutor


class UnknownDecision:
    pass


@pytest.mark.asyncio
async def test_executor_decision_handling():
    network = MagicMock()
    tm = MagicMock(spec=TaskManager)
    pm = MagicMock(spec=PoolManager)

    executor = StandardExecutor("agent1", network, tm, pm)

    tm.claim.return_value = False
    await executor.execute([ClaimTask("t1")])
    tm.claim.assert_called_with("agent1", "t1")

    await executor.execute([UnknownDecision()])

    await executor.execute([JoinPool("p1")])
    pm.join_pool.assert_called_with("agent1", "p1")


@pytest.mark.asyncio
async def test_executor_send_message():
    from unittest.mock import AsyncMock

    network = MagicMock()
    network.send = AsyncMock(return_value=None)
    tm = MagicMock(spec=TaskManager)
    pm = MagicMock(spec=PoolManager)
    executor = StandardExecutor("agent1", network, tm, pm)
    msg = Message(sender="agent1", payload={"body": "hello"})
    await executor.execute([SendMessage(message=msg)])
    network.send.assert_called_once()
    (call_arg,) = network.send.call_args[0]
    assert call_arg is msg


@pytest.mark.asyncio
async def test_executor_submit_task():
    network = MagicMock()
    tm = MagicMock(spec=TaskManager)
    pm = MagicMock(spec=PoolManager)
    executor = StandardExecutor("agent1", network, tm, pm)
    task = Task()
    await executor.execute([SubmitTask(task=task)])
    tm.submit.assert_called_once_with(task)


@pytest.mark.asyncio
async def test_executor_leave_pool_create_pool_report_task():
    network = MagicMock()
    tm = MagicMock(spec=TaskManager)
    pm = MagicMock(spec=PoolManager)
    executor = StandardExecutor("agent1", network, tm, pm)
    await executor.execute([
        LeavePool("p1"),
        CreatePool({"topics": []}),
    ])
    pm.leave_pool.assert_called_with("agent1", "p1")
    pm.create_pool.assert_called_once_with({"topics": []})
    tm.report.assert_not_called()
    await executor.execute([ReportTask("task1", {"result": "ok"})])
    tm.report.assert_called_with("agent1", "task1", {"result": "ok"})


@pytest.mark.asyncio
async def test_executor_protocol_default_execute():
    class StubExecutor:
        async def execute(self, decisions):
            pass

    stub = StubExecutor()
    await Executor.execute(stub, [])


@pytest.mark.asyncio
async def test_executor_create_pool_report_task():
    from converge.network.transport.local import LocalTransport

    identity = Identity.generate()
    transport = LocalTransport(identity.fingerprint)
    await transport.start()
    tm = TaskManager()
    pm = PoolManager()
    exec_ = StandardExecutor(identity.fingerprint, None, tm, pm)
    task = Task(id="t1", objective={})
    tm.submit(task)
    tm.claim(identity.fingerprint, "t1")
    await exec_.execute([
        CreatePool({"id": "p1", "topics": []}),
        ReportTask("t1", "done"),
    ])
    assert "p1" in pm.pools
    assert tm.get_task("t1").result == "done"
    await transport.stop()


@pytest.mark.asyncio
async def test_executor_metrics_and_claim_failure():

    from converge.network.network import AgentNetwork
    from converge.network.transport.local import LocalTransport
    from converge.observability.metrics import MetricsCollector

    identity = Identity.generate()
    transport = LocalTransport(identity.fingerprint)
    await transport.start()
    network = AgentNetwork(transport)
    tm = TaskManager()
    pm = PoolManager()
    metrics = MetricsCollector()

    exec_ = StandardExecutor(identity.fingerprint, network, tm, pm, metrics_collector=metrics)
    await exec_.execute([ClaimTask("nonexistent")])
    assert metrics.snapshot()["counters"].get("decisions_executed", 0) == 1

    pm.create_pool({"id": "p1", "topics": []})
    await exec_.execute([JoinPool("p1"), LeavePool("p1")])

    await transport.stop()


@pytest.mark.asyncio
async def test_executor_send_message_with_metrics():
    """SendMessage with network and metrics_collector covers messages_sent inc."""
    from unittest.mock import AsyncMock

    from converge.observability.metrics import MetricsCollector

    network = MagicMock()
    network.send = AsyncMock(return_value=None)
    tm = MagicMock(spec=TaskManager)
    pm = MagicMock(spec=PoolManager)
    metrics = MetricsCollector()
    executor = StandardExecutor("agent1", network, tm, pm, metrics_collector=metrics)
    msg = Message(sender="agent1", payload={})
    await executor.execute([SendMessage(message=msg)])
    assert metrics.snapshot()["counters"].get("messages_sent", 0) == 1


@pytest.mark.asyncio
async def test_executor_edges():
    from converge.core.decisions import SubmitTask

    network = MagicMock()
    tm = MagicMock(spec=TaskManager)
    tm.submit.side_effect = Exception("error")
    executor = StandardExecutor("a1", network, tm, MagicMock())
    await executor.execute([SubmitTask(Task())])


@pytest.mark.asyncio
async def test_executor_send_message_network_none():
    """SendMessage with network=None does not call network.send."""
    tm = MagicMock(spec=TaskManager)
    pm = MagicMock(spec=PoolManager)
    executor = StandardExecutor("agent1", None, tm, pm)
    msg = Message(sender="agent1", payload={"x": 1})
    await executor.execute([SendMessage(message=msg)])
    # No crash; network.send never called
