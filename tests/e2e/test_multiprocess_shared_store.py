"""E2E: separate processes coordinate through shared SQLite store."""

import asyncio
import multiprocessing as mp
import time
from pathlib import Path

from converge.coordination.pool_manager import PoolManager
from converge.coordination.task_manager import TaskManager
from converge.core.agent import Agent
from converge.core.decisions import ClaimTask, ReportTask
from converge.core.identity import Identity
from converge.core.task import Task, TaskState
from converge.extensions.storage.sqlite_store import SQLiteStore
from converge.network.discovery import DiscoveryService
from converge.network.network import build_descriptor
from converge.network.transport.local import LocalTransport
from converge.runtime.loop import AgentRuntime


class _WorkerAgent(Agent):
    def decide(self, messages, tasks):
        if not tasks:
            return []
        task = tasks[0]
        return [ClaimTask(task.id), ReportTask(task.id, {"status": "done-by-worker-process"})]


def _worker_process(db_path: str, task_id: str) -> int:
    async def run() -> int:
        store = SQLiteStore(path=db_path)
        task_manager = TaskManager(store=store)
        pool_manager = PoolManager(store=store)
        discovery = DiscoveryService(store=store)
        identity = Identity.generate()
        agent = _WorkerAgent(identity)
        runtime = AgentRuntime(
            agent=agent,
            transport=LocalTransport(agent.id),
            pool_manager=pool_manager,
            task_manager=task_manager,
            discovery_service=discovery,
            agent_descriptor=build_descriptor(agent),
            scheduler_timeout_sec=0.1,
            task_refresh_interval_sec=0.05,
        )
        await runtime.start()
        try:
            deadline = time.monotonic() + 8.0
            while time.monotonic() < deadline:
                await asyncio.sleep(0.05)
                task_manager.refresh_from_store()
                task = task_manager.get_task(task_id)
                if task is not None and task.state == TaskState.COMPLETED:
                    return 0
            return 2
        finally:
            await runtime.stop()

    return asyncio.run(run())


def test_e2e_multiprocess_shared_sqlite_visibility(tmp_path: Path):
    db_path = tmp_path / "shared.sqlite3"
    store = SQLiteStore(path=db_path)
    parent_tm = TaskManager(store=store)
    task_id = parent_tm.submit(Task(objective={"job": "from-parent"}))

    ctx = mp.get_context("spawn")
    proc = ctx.Process(target=_worker_process, args=(str(db_path), task_id))
    proc.start()
    proc.join(timeout=15)

    assert proc.exitcode == 0

    parent_tm.refresh_from_store()
    task = parent_tm.get_task(task_id)
    assert task is not None
    assert task.state == TaskState.COMPLETED
    assert task.result == {"status": "done-by-worker-process"}

    # Worker runtime should have unregistered from discovery on stop.
    assert store.list("discovery:agent:") == []
