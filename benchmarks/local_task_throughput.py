#!/usr/bin/env python3
"""
Minimal benchmark: task submit/claim/report throughput with in-memory store and local transport.
Run: python benchmarks/local_task_throughput.py
Optional: N env var (default 100 tasks).
"""
import os
import time

from converge.coordination.pool_manager import PoolManager
from converge.coordination.task_manager import TaskManager
from converge.core.task import Task
from converge.extensions.storage.memory import MemoryStore

N = int(os.environ.get("N", 100))


def main():
    store = MemoryStore()
    pm = PoolManager(store=store)
    tm = TaskManager(store=store)
    pool = pm.create_pool({"id": "bm", "topics": []})
    pm.join_pool("agent1", pool.id)

    # Submit N tasks
    t0 = time.perf_counter()
    for i in range(N):
        task = Task(objective={"i": i}, inputs={})
        tm.submit(task)
    submit_elapsed = time.perf_counter() - t0

    # Claim and report all
    task_ids = [t.id for t in tm.list_pending_tasks()]
    t0 = time.perf_counter()
    for tid in task_ids:
        tm.claim("agent1", tid)
        tm.report("agent1", tid, "ok")
    claim_report_elapsed = time.perf_counter() - t0

    print(f"Tasks: {N}")
    print(f"Submit {N} tasks: {submit_elapsed:.3f}s ({N/submit_elapsed:.0f} tasks/s)")
    print(f"Claim+report {N} tasks: {claim_report_elapsed:.3f}s ({N/claim_report_elapsed:.0f} tasks/s)")


if __name__ == "__main__":
    main()
