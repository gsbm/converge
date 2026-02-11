"""E2E chaos-style: one runtime claims a task then stops without reporting; release_expired_claims; another agent can claim."""

import asyncio
import time

import pytest

from converge.coordination.pool_manager import PoolManager
from converge.coordination.task_manager import TaskManager
from converge.core.agent import Agent
from converge.core.decisions import ClaimTask, ReportTask
from converge.core.identity import Identity
from converge.core.task import Task
from converge.extensions.storage.memory import MemoryStore
from converge.network.transport.local import LocalTransport, LocalTransportRegistry
from converge.runtime.loop import AgentRuntime


class ClaimOnlyAgent(Agent):
    """Claims the first task but does not report (simulates crash)."""

    def decide(self, messages, tasks):
        if not tasks:
            return []
        return [ClaimTask(tasks[0].id)]


class WorkerAgent(Agent):
    """Claims first task and reports."""

    def decide(self, messages, tasks):
        if not tasks:
            return []
        t = tasks[0]
        return [ClaimTask(t.id), ReportTask(t.id, "recovered")]


@pytest.fixture
def registry():
    reg = LocalTransportRegistry()
    reg.clear()
    return reg


@pytest.mark.asyncio
async def test_e2e_chaos_claim_then_release_expired_other_claims(registry):
    """First runtime claims task and stops without report; release_expired_claims; second agent claims and reports."""
    store = MemoryStore()
    pm = PoolManager(store=store)
    tm = TaskManager(store=store)

    pool = pm.create_pool({"id": "chaos-pool", "topics": []})
    task = Task(
        objective={"chaos": True},
        inputs={},
        constraints={"claim_ttl_sec": 0.2},
    )
    task_id = tm.submit(task)

    # Agent 1: claim then "crash" (stop without report)
    id1 = Identity.generate()
    agent1 = ClaimOnlyAgent(id1)
    trans1 = LocalTransport(agent1.id)
    runtime1 = AgentRuntime(
        agent=agent1,
        transport=trans1,
        pool_manager=pm,
        task_manager=tm,
    )
    await runtime1.start()
    pm.join_pool(agent1.id, pool.id)

    for _ in range(20):
        await asyncio.sleep(0.05)
        if tm.get_task(task_id).state.value == "assigned":
            break
    assert tm.get_task(task_id).state.value == "assigned"

    await runtime1.stop()

    # Wait for claim TTL to elapse
    time.sleep(0.3)

    # Release expired claims
    released = tm.release_expired_claims(time.monotonic())
    assert task_id in released
    assert tm.get_task(task_id).state.value == "pending"

    # Agent 2: claim and report
    id2 = Identity.generate()
    agent2 = WorkerAgent(id2)
    trans2 = LocalTransport(agent2.id)
    runtime2 = AgentRuntime(
        agent=agent2,
        transport=trans2,
        pool_manager=pm,
        task_manager=tm,
    )
    await runtime2.start()
    pm.join_pool(agent2.id, pool.id)

    for _ in range(30):
        await asyncio.sleep(0.1)
        t = tm.get_task(task_id)
        if t is not None and t.state.value == "completed":
            break
    else:
        await runtime2.stop()
        pytest.fail("Task not completed by second agent")

    assert tm.get_task(task_id).result == "recovered"
    await runtime2.stop()
