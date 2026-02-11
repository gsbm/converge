"""Integration test: agent with tool_registry executes InvokeTool."""

import asyncio

from converge.coordination.pool_manager import PoolManager
from converge.coordination.task_manager import TaskManager
from converge.core.agent import Agent
from converge.core.decisions import InvokeTool
from converge.core.identity import Identity
from converge.extensions.storage.memory import MemoryStore
from converge.network.transport.local import LocalTransport, LocalTransportRegistry
from converge.runtime.loop import AgentRuntime


class _AgentWithToolDecision(Agent):
    """Agent that responds to any message by emitting InvokeTool('echo', {})."""

    def decide(self, messages, tasks):
        if messages:
            return [InvokeTool(tool_name="echo", params={"called": True})]
        return []


async def test_agent_invoke_tool_integration():
    """Run runtime with a tool; agent emits InvokeTool; executor runs the tool."""
    registry = LocalTransportRegistry()
    registry.clear()

    class EchoTool:
        @property
        def name(self) -> str:
            return "echo"

        def run(self, params: dict):
            self.result = params
            return "ok"

    echo_tool = EchoTool()
    from converge.core.tools import ToolRegistry
    tool_registry = ToolRegistry()
    tool_registry.register(echo_tool)

    identity = Identity.generate()
    agent = _AgentWithToolDecision(identity)
    transport = LocalTransport(agent.id)
    pool_manager = PoolManager(store=MemoryStore())
    task_manager = TaskManager(store=MemoryStore())

    runtime = AgentRuntime(
        agent=agent,
        transport=transport,
        pool_manager=pool_manager,
        task_manager=task_manager,
        tool_registry=tool_registry,
    )

    async def run_and_send():
        await runtime.start()
        queue = registry.get_queue(agent.id)
        assert queue is not None
        from converge.core.message import Message
        await queue.put(Message(sender="other", recipient=agent.id, payload={}))
        await asyncio.sleep(0.4)
        await runtime.stop()

    await run_and_send()

    assert getattr(echo_tool, "result", None) == {"called": True}
