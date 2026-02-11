"""Tests for converge.runtime.executor."""

from unittest.mock import MagicMock

import pytest

from converge.coordination.pool_manager import PoolManager
from converge.coordination.task_manager import TaskManager
from converge.core.decisions import (
    AcceptProposal,
    ClaimTask,
    CreatePool,
    Delegate,
    InvokeTool,
    JoinPool,
    LeavePool,
    Propose,
    RejectProposal,
    ReportTask,
    RevokeDelegation,
    SendMessage,
    SubmitBid,
    SubmitTask,
    Vote,
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


@pytest.mark.asyncio
async def test_executor_coordination_decisions():
    """SubmitBid, Vote, Propose, AcceptProposal, RejectProposal, Delegate, RevokeDelegation."""
    from converge.coordination.bidding import BiddingProtocol
    from converge.coordination.delegation import DelegationProtocol
    from converge.coordination.negotiation import NegotiationProtocol

    network = MagicMock()
    tm = MagicMock(spec=TaskManager)
    pm = MagicMock(spec=PoolManager)
    bidding = BiddingProtocol()
    negotiation = NegotiationProtocol()
    delegation = DelegationProtocol()
    votes_store = {}

    executor = StandardExecutor(
        "agent1",
        network,
        tm,
        pm,
        bidding_protocols={"auc1": bidding},
        negotiation_protocol=negotiation,
        delegation_protocol=delegation,
        votes_store=votes_store,
    )

    await executor.execute([SubmitBid(auction_id="auc1", amount=10.0, content={"sla": 1})])
    assert bidding.bids.get("agent1") == 10.0

    await executor.execute([Vote(vote_id="v1", option="A")])
    assert votes_store.get("v1") == [("agent1", "A")]

    session_id = negotiation.create_session("agent1", ["agent2"], initial_proposal={"x": 1})
    await executor.execute([Propose(session_id=session_id, proposal_content={"x": 2})])
    await executor.execute([AcceptProposal(session_id=session_id)])
    assert negotiation.get_session(session_id).state.value == "accepted"

    sid2 = negotiation.create_session("agent1", ["agent2"], initial_proposal={})
    await executor.execute([RejectProposal(session_id=sid2)])
    assert negotiation.get_session(sid2).state.value == "rejected"

    await executor.execute([Delegate(delegatee_id="agent2", scope=["topic:a"])])
    assert len(delegation.delegations) == 1
    did = next(iter(delegation.delegations))
    await executor.execute([RevokeDelegation(delegation_id=did)])
    assert delegation.delegations[did]["active"] is False


@pytest.mark.asyncio
async def test_executor_invoke_tool():
    """InvokeTool runs the tool from tool_registry with params."""
    from converge.core.tools import ToolRegistry

    class RecordingTool:
        @property
        def name(self) -> str:
            return "rec"

        def run(self, params: dict):
            self.called = params
            return "ok"

    tool = RecordingTool()
    registry = ToolRegistry()
    registry.register(tool)

    network = MagicMock()
    tm = MagicMock(spec=TaskManager)
    pm = MagicMock(spec=PoolManager)
    executor = StandardExecutor("agent1", network, tm, pm, tool_registry=registry)

    await executor.execute([InvokeTool(tool_name="rec", params={"x": 1})])
    assert getattr(tool, "called", None) == {"x": 1}


@pytest.mark.asyncio
async def test_executor_invoke_tool_unknown_ignored():
    """InvokeTool with unknown tool name does not raise when tool_registry is set."""
    from converge.core.tools import ToolRegistry

    registry = ToolRegistry()
    network = MagicMock()
    tm = MagicMock(spec=TaskManager)
    pm = MagicMock(spec=PoolManager)
    executor = StandardExecutor("agent1", network, tm, pm, tool_registry=registry)
    await executor.execute([InvokeTool(tool_name="nonexistent", params={})])


@pytest.mark.asyncio
async def test_executor_tool_allowlist_rejects_unknown():
    """InvokeTool with tool_allowlist set skips tool not in allowlist and does not run it."""
    from converge.core.tools import ToolRegistry

    class ToolA:
        @property
        def name(self) -> str:
            return "tool_a"

        def run(self, params: dict):
            return "ran"

    registry = ToolRegistry()
    registry.register(ToolA())
    network = MagicMock()
    tm = MagicMock(spec=TaskManager)
    pm = MagicMock(spec=PoolManager)
    executor = StandardExecutor(
        "agent1", network, tm, pm,
        tool_registry=registry,
        tool_allowlist={"tool_a"},
    )
    # Allowed: runs
    await executor.execute([InvokeTool(tool_name="tool_a", params={})])

    # Not in allowlist: skipped (tool_b not in registry anyway; allowlist is checked first)
    executor2 = StandardExecutor(
        "agent1", network, tm, pm,
        tool_registry=registry,
        tool_allowlist={"tool_a"},
    )
    await executor2.execute([InvokeTool(tool_name="other_tool", params={})])
    # No crash; other_tool is skipped by allowlist


@pytest.mark.asyncio
async def test_executor_tool_timeout():
    """InvokeTool with tool_timeout_sec times out on slow tool and does not crash."""
    import time

    from converge.core.tools import ToolRegistry

    class SlowTool:
        @property
        def name(self) -> str:
            return "slow"

        def run(self, params: dict):
            time.sleep(2.0)
            return "done"

    registry = ToolRegistry()
    registry.register(SlowTool())
    network = MagicMock()
    tm = MagicMock(spec=TaskManager)
    pm = MagicMock(spec=PoolManager)
    executor = StandardExecutor(
        "agent1", network, tm, pm,
        tool_registry=registry,
        tool_timeout_sec=0.05,
    )
    await executor.execute([InvokeTool(tool_name="slow", params={})])
    # Timeout occurs; no crash (executor catches TimeoutError and logs)


@pytest.mark.asyncio
async def test_executor_custom_handlers():
    """Custom decision types can be handled via custom_handlers."""
    from dataclasses import dataclass

    from converge.core.decisions import Decision

    @dataclass
    class CustomDecision(Decision):
        value: str

    seen = []

    async def handle_custom(decision: CustomDecision):
        seen.append(decision.value)

    network = MagicMock()
    tm = MagicMock(spec=TaskManager)
    pm = MagicMock(spec=PoolManager)
    executor = StandardExecutor(
        "agent1", network, tm, pm,
        custom_handlers={CustomDecision: handle_custom},
    )
    await executor.execute([CustomDecision(value="hello")])
    assert seen == ["hello"]
