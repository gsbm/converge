"""E2E: restart recovery - task persisted in FileStore survives runtime stop/start and can be claimed/reported."""

import asyncio

import pytest

from converge.coordination.pool_manager import PoolManager
from converge.coordination.task_manager import TaskManager
from converge.core.agent import Agent
from converge.core.decisions import ClaimTask, ReportTask
from converge.core.identity import Identity
from converge.core.task import Task
from converge.extensions.storage.file import FileStore
from converge.network.transport.local import LocalTransport, LocalTransportRegistry
from converge.runtime.loop import AgentRuntime


class WorkerAgent(Agent):
    """Claims first pending task and reports it."""

    def decide(self, messages, tasks):
        if not tasks:
            return []
        t = tasks[0]
        return [ClaimTask(t.id), ReportTask(t.id, {"done": True})]


@pytest.fixture
def registry():
    reg = LocalTransportRegistry()
    reg.clear()
    return reg


@pytest.mark.asyncio
async def test_e2e_restart_recovery_task_persisted_then_claimed(registry, tmp_path):
    """Run agent with FileStore; submit task; stop runtime; restart with same store; task still present; agent claims and reports."""
    store_path = tmp_path / "e2e_recovery_store"
    store_path.mkdir()
    store = FileStore(base_path=str(store_path))

    pm = PoolManager(store=store)
    tm = TaskManager(store=store)

    pool = pm.create_pool({"id": "recovery-pool", "topics": []})
    task = Task(objective={"restart_test": True}, inputs={})
    task_id = tm.submit(task)

    identity = Identity.generate()
    agent = WorkerAgent(identity)
    transport = LocalTransport(agent.id)

    runtime = AgentRuntime(
        agent=agent,
        transport=transport,
        pool_manager=pm,
        task_manager=tm,
    )
    await runtime.start()
    pm.join_pool(agent.id, pool.id)

    # Let one tick run then stop (task may or may not be claimed yet)
    await asyncio.sleep(0.3)
    await runtime.stop()

    # Restart with same store
    pm2 = PoolManager(store=store)
    tm2 = TaskManager(store=store)
    restored = tm2.get_task(task_id)
    assert restored is not None
    assert restored.state.value in ("pending", "assigned", "completed")

    # If still pending, start again and let agent claim and report
    agent2 = WorkerAgent(identity)
    transport2 = LocalTransport(agent2.id)
    runtime2 = AgentRuntime(
        agent=agent2,
        transport=transport2,
        pool_manager=pm2,
        task_manager=tm2,
    )
    await runtime2.start()
    pm2.join_pool(agent2.id, pool.id)

    for _ in range(30):
        await asyncio.sleep(0.1)
        t = tm2.get_task(task_id)
        if t is not None and t.state.value == "completed":
            break
    else:
        await runtime2.stop()
        pytest.fail("Task not completed after restart")

    assert tm2.get_task(task_id).result == {"done": True}
    await runtime2.stop()
