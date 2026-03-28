#!/usr/bin/env python3
"""
Benchmark pending-task visibility refresh and filtering.

Run:
  .venv/bin/python benchmarks/pending_task_visibility.py
Optional env:
  N=5000 REFRESH=1
"""

import os
import time

from converge.coordination.task_manager import TaskManager
from converge.core.task import Task
from converge.extensions.storage.memory import MemoryStore

N = int(os.environ.get("N", "5000"))
REFRESH = os.environ.get("REFRESH", "1") == "1"


def main() -> None:
    store = MemoryStore()
    tm = TaskManager(store=store)

    t0 = time.perf_counter()
    for i in range(N):
        tm.submit(Task(objective={"i": i}))
    submit_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    visible = tm.list_pending_tasks_for_agent(
        "agent1",
        pool_ids=None,
        capabilities=None,
        refresh_from_store=REFRESH,
    )
    list_s = time.perf_counter() - t0

    print(f"N={N} refresh={REFRESH}")
    print(f"submit: {submit_s:.4f}s ({N/submit_s:.0f} tasks/s)")
    print(f"list_visible: {list_s:.4f}s ({len(visible)/max(list_s, 1e-9):.0f} tasks/s)")


if __name__ == "__main__":
    main()
