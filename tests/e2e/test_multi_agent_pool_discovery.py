"""E2E: multi-agent with discovery and pool; one agent claims and reports a task."""

import asyncio

import pytest

from converge.coordination.pool_manager import PoolManager
from converge.coordination.task_manager import TaskManager
from converge.core.agent import Agent
from converge.core.decisions import ClaimTask, ReportTask
from converge.core.identity import Identity
from converge.core.task import Task
from converge.extensions.storage.memory import MemoryStore
from converge.network.discovery import DiscoveryService
from converge.network.network import build_descriptor
from converge.network.transport.local import LocalTransport, LocalTransportRegistry
from converge.runtime.loop import AgentRuntime


class WorkerAgent(Agent):
    """Agent that claims the first pending task and reports it done."""

    def decide(self, messages, tasks):
        if not tasks:
            return []
        t = tasks[0]
        return [ClaimTask(t.id), ReportTask(t.id, {"status": "done"})]


@pytest.fixture
def registry():
    reg = LocalTransportRegistry()
    reg.clear()
    return reg


@pytest.mark.asyncio
async def test_e2e_multi_agent_discovery_pool_task(registry):
    """Start 2 agents with shared PoolManager, TaskManager, discovery store; create pool, join, submit task; one claims and reports; assert completed and discovery finds agents."""
    store = MemoryStore()
    pm = PoolManager(store=store)
    tm = TaskManager(store=store)
    discovery = DiscoveryService(store=store)

    pool = pm.create_pool({"id": "e2e-pool", "topics": []})
    task = Task(objective={"job": "test"}, inputs={})
    task_id = tm.submit(task)

    id1 = Identity.generate()
    id2 = Identity.generate()
    agent1 = WorkerAgent(id1)
    agent2 = WorkerAgent(id2)

    trans1 = LocalTransport(agent1.id)
    trans2 = LocalTransport(agent2.id)

    runtime1 = AgentRuntime(
        agent=agent1,
        transport=trans1,
        pool_manager=pm,
        task_manager=tm,
        discovery_service=discovery,
        agent_descriptor=build_descriptor(agent1),
    )
    runtime2 = AgentRuntime(
        agent=agent2,
        transport=trans2,
        pool_manager=pm,
        task_manager=tm,
        discovery_service=discovery,
        agent_descriptor=build_descriptor(agent2),
    )

    await runtime1.start()
    await runtime2.start()

    # Both agents joined pool (done in test by joining after runtime start - we need to join them to the pool)
    pm.join_pool(agent1.id, pool.id)
    pm.join_pool(agent2.id, pool.id)

    # Wait for one agent to claim and report (poll task state)
    for _ in range(50):
        await asyncio.sleep(0.1)
        t = tm.get_task(task_id)
        if t is not None and t.state.value == "completed":
            break
    else:
        await runtime1.stop()
        await runtime2.stop()
        pytest.fail("Task was not completed within timeout")

    assert tm.get_task(task_id).result == {"status": "done"}

    # Discovery has both agents registered
    assert agent1.id in discovery.descriptors
    assert agent2.id in discovery.descriptors

    await runtime1.stop()
    await runtime2.stop()
