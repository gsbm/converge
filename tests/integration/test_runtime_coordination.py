"""Integration tests: runtime with pool manager and task manager."""

import asyncio

import pytest

from converge.coordination.pool_manager import PoolManager
from converge.coordination.task_manager import TaskManager
from converge.core.agent import Agent
from converge.core.decisions import ClaimTask, CreatePool, JoinPool, LeavePool, ReportTask, SubmitTask
from converge.core.identity import Identity
from converge.core.message import Message
from converge.core.task import Task, TaskState
from converge.network.transport.local import LocalTransport
from converge.runtime.loop import AgentRuntime


class CoordinationAgent(Agent):
    def __init__(self, identity, actions_to_take):
        super().__init__(identity=identity)
        self.actions_to_take = actions_to_take
        self.call_count = 0

    def decide(self, messages, tasks):
        if self.call_count < len(self.actions_to_take):
            decisions = self.actions_to_take[self.call_count]
            self.call_count += 1
            return decisions
        return []


@pytest.mark.asyncio
async def test_runtime_coordination_integration():
    id_a = Identity.generate()
    pm = PoolManager()
    tm = TaskManager()
    transport = LocalTransport(id_a.fingerprint)

    pool = pm.create_pool({})

    task = Task()
    actions = [
        [JoinPool(pool_id=pool.id)],
        [SubmitTask(task=task)],
        [ClaimTask(task_id=task.id)],
    ]

    agent = CoordinationAgent(identity=id_a, actions_to_take=actions)
    runtime = AgentRuntime(agent=agent, transport=transport, pool_manager=pm, task_manager=tm)

    await runtime.start()

    for _ in range(3):
        dummy = Message(sender="system", payload={"type": "tick"})
        await runtime.inbox.push(dummy)
        runtime.scheduler.notify()
        await asyncio.sleep(0.1)

    assert id_a.fingerprint in pool.agents

    stored_task = tm.get_task(task.id)
    assert stored_task is not None
    assert stored_task.id == task.id

    assert stored_task.assigned_to == id_a.fingerprint

    await runtime.stop()


@pytest.mark.asyncio
async def test_runtime_additional_decisions():
    id_a = Identity.generate()
    pm = PoolManager()
    tm = TaskManager()
    transport = LocalTransport(id_a.fingerprint)

    task = Task()
    tm.submit(task)
    task.assigned_to = id_a.fingerprint
    task.state = TaskState.ASSIGNED

    actions = [
        [CreatePool(spec={"id": "custom_pool"})],
        [LeavePool(pool_id="custom_pool")],
        [ReportTask(task_id=task.id, result="done")],
    ]

    agent = CoordinationAgent(identity=id_a, actions_to_take=actions)
    runtime = AgentRuntime(agent=agent, transport=transport, pool_manager=pm, task_manager=tm)

    await runtime.start()

    for _ in range(3):
        await runtime.inbox.push(Message(sender="sys", payload="tick"))
        runtime.scheduler.notify()
        await asyncio.sleep(0.05)

    assert "custom_pool" in pm.pools

    t = tm.get_task(task.id)
    assert t.state == TaskState.COMPLETED
    assert t.result == "done"

    await runtime.stop()


@pytest.mark.asyncio
async def test_pool_manager_persistence():
    from converge.extensions.storage.memory import MemoryStore

    store = MemoryStore()
    pm = PoolManager(store)

    pool = pm.create_pool({"id": "p1"})

    assert store.get("pool:p1") == pool

    pm2 = PoolManager(store)
    pool2 = pm2.get_pool("p1")
    assert pool2 is not None
    assert pool2.id == "p1"
