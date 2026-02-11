"""Tests for converge.coordination.task_manager."""

import pytest

from converge.coordination.task_manager import TaskManager
from converge.core.task import Task, TaskState
from converge.extensions.storage.memory import MemoryStore


def test_task_manager_flow():
    tm = TaskManager()

    task = Task(objective={"type": "compute"})
    task_id = tm.submit(task)
    assert task_id == task.id
    assert tm.get_task(task_id) is task

    assert len(tm.list_pending_tasks()) == 1

    agent_id = "agent1"
    success = tm.claim(agent_id, task_id)
    assert success
    assert task.state == TaskState.ASSIGNED
    assert task.assigned_to == agent_id

    assert len(tm.list_pending_tasks()) == 0

    tm.report(agent_id, task_id, result="42")
    assert task.state == TaskState.COMPLETED
    assert task.result == "42"


def test_task_claim_invalid():
    tm = TaskManager()
    task = Task()
    tm.submit(task)

    assert tm.claim("agent1", task.id)
    assert not tm.claim("agent2", task.id)


def test_task_manager_persistence_reload():
    store = MemoryStore()
    tm1 = TaskManager(store)

    task = Task()
    tm1.submit(task)

    tm2 = TaskManager(store)
    loaded_task = tm2.get_task(task.id)
    assert loaded_task is not None
    assert loaded_task.id == task.id

    assert tm2.claim("agent1", task.id)
    assert tm2.get_task(task.id).state == TaskState.ASSIGNED
    assert store.get(f"task:{task.id}").state == TaskState.ASSIGNED

    tm2.report("agent1", task.id, "result")
    assert tm2.get_task(task.id).state == TaskState.COMPLETED


def test_task_manager_cache_miss_actions():
    store = MemoryStore()

    tm1 = TaskManager(store)
    task1 = Task()
    tm1.submit(task1)

    tm2 = TaskManager(store)
    success = tm2.claim("agent1", task1.id)
    assert success
    assert tm2.get_task(task1.id).state == TaskState.ASSIGNED

    task2 = Task()
    tm1.submit(task2)
    tm1.claim("agent1", task2.id)

    tm3 = TaskManager(store)
    tm3.report("agent1", task2.id, "result")
    t2 = tm3.get_task(task2.id)
    assert t2.state == TaskState.COMPLETED
    assert t2.result == "result"


def test_task_manager_get_task_loads_from_store():
    store = MemoryStore()
    tm1 = TaskManager(store)
    task = Task()
    tm1.submit(task)
    tm2 = TaskManager(store)
    assert task.id not in tm2.tasks
    loaded = tm2.get_task(task.id)
    assert loaded is not None
    assert loaded.id == task.id
    assert task.id in tm2.tasks


def test_task_manager_edge_cases():
    tm = TaskManager()
    task = Task()
    tm.submit(task)
    tm.claim("agent1", task.id)

    with pytest.raises(ValueError, match="not authorized"):
        tm.report("agent2", task.id, "result")

    assert not tm.claim("agent1", "missing_id")
    tm.report("agent1", "missing_id", "result")


def test_task_manager_branch():
    tm = TaskManager()
    tm.report("a1", "non-existent", {})


def test_task_manager_report_nonexistent_task_no_raise():
    """report() when task not in cache and not in store returns without raising."""
    store = MemoryStore()
    tm = TaskManager(store)
    tm.report("agent1", "nonexistent_id", "result")


def test_task_manager_get_task_from_store_pending_adds_to_pending():
    """get_task loads from store and adds to pending_task_ids when state is PENDING."""
    store = MemoryStore()
    tm1 = TaskManager(store)
    task = Task()
    tm1.submit(task)
    tm2 = TaskManager(store)
    assert task.id not in tm2.tasks
    loaded = tm2.get_task(task.id)
    assert loaded is not None
    assert task.id in tm2.pending_task_ids


def test_task_manager_get_task_from_store_non_pending_does_not_add_to_pending():
    """get_task loads from store but does not add to pending_task_ids when state is not PENDING."""
    store = MemoryStore()
    tm1 = TaskManager(store)
    task = Task()
    tm1.submit(task)
    tm1.claim("agent1", task.id)
    tm2 = TaskManager(store)
    loaded = tm2.get_task(task.id)
    assert loaded is not None
    assert loaded.state == TaskState.ASSIGNED
    assert task.id not in tm2.pending_task_ids


def test_list_pending_tasks_for_agent_no_filter_returns_all():
    """When pool_ids and capabilities are None, all pending tasks are returned."""
    tm = TaskManager()
    t1 = Task()
    t2 = Task(pool_id="p1", required_capabilities=["x"])
    tm.submit(t1)
    tm.submit(t2)
    result = tm.list_pending_tasks_for_agent("agent1", pool_ids=None, capabilities=None)
    assert len(result) == 2


def test_list_pending_tasks_for_agent_filter_by_pool():
    """Tasks with pool_id are only included when agent is in that pool."""
    tm = TaskManager()
    t1 = Task(pool_id="pool_a")
    t2 = Task(pool_id="pool_b")
    t3 = Task()  # no pool
    tm.submit(t1)
    tm.submit(t2)
    tm.submit(t3)
    # Agent in pool_a only
    result = tm.list_pending_tasks_for_agent("agent1", pool_ids=["pool_a"], capabilities=None)
    assert len(result) == 2  # t1 and t3 (no pool)
    ids = {t.id for t in result}
    assert t1.id in ids
    assert t3.id in ids
    assert t2.id not in ids


def test_list_pending_tasks_for_agent_filter_by_capabilities():
    """Tasks with required_capabilities are only included when agent has all of them."""
    tm = TaskManager()
    t1 = Task(required_capabilities=["a", "b"])
    t2 = Task(required_capabilities=["a"])
    t3 = Task()
    tm.submit(t1)
    tm.submit(t2)
    tm.submit(t3)
    result = tm.list_pending_tasks_for_agent("agent1", pool_ids=None, capabilities=["a", "b"])
    assert len(result) == 3
    result_missing = tm.list_pending_tasks_for_agent("agent2", pool_ids=None, capabilities=["a"])
    assert len(result_missing) == 2  # t2 and t3, not t1
    ids_missing = {t.id for t in result_missing}
    assert t1.id not in ids_missing


def test_list_pending_tasks_for_agent_combined_filters():
    """Pool and capability filters are both applied."""
    tm = TaskManager()
    t1 = Task(pool_id="p1", required_capabilities=["x"])
    t2 = Task(pool_id="p1")
    t3 = Task(pool_id="p2", required_capabilities=["x"])
    tm.submit(t1)
    tm.submit(t2)
    tm.submit(t3)
    result = tm.list_pending_tasks_for_agent("a1", pool_ids=["p1", "p2"], capabilities=["x"])
    assert len(result) == 3
    result_p1_only = tm.list_pending_tasks_for_agent("a2", pool_ids=["p1"], capabilities=["x"])
    ids_p1 = {t.id for t in result_p1_only}
    assert t1.id in ids_p1
    assert t2.id in ids_p1
    assert t3.id not in ids_p1
