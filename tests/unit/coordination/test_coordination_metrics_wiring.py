"""Tests for coordination metrics wiring in managers."""

from converge.coordination.pool_manager import PoolManager
from converge.coordination.task_manager import TaskManager
from converge.core.task import Task
from converge.observability.coordination_metrics import CoordinationMetrics
from converge.observability.metrics import MetricsCollector


def test_task_manager_emits_structured_metrics():
    collector = MetricsCollector()
    metrics = CoordinationMetrics(collector)
    manager = TaskManager(coordination_metrics=metrics)
    task = Task(objective={"x": 1})

    task_id = manager.submit(task)
    assert collector.snapshot()["counters"]["task_submitted_total"] == 1
    assert collector.snapshot()["gauges"]["pending_tasks"] == 1

    assert manager.claim("a1", task_id) is True
    assert collector.snapshot()["counters"]["task_claimed_total"] == 1
    assert collector.snapshot()["gauges"]["pending_tasks"] == 0

    manager.report("a1", task_id, {"ok": True})
    assert collector.snapshot()["counters"]["task_completed_total"] == 1


def test_pool_manager_emits_structured_metrics():
    collector = MetricsCollector()
    metrics = CoordinationMetrics(collector)
    manager = PoolManager(coordination_metrics=metrics)

    pool = manager.create_pool({"id": "p1", "topics": []})
    assert collector.snapshot()["counters"]["pool_created_total"] == 1
    assert collector.snapshot()["gauges"]["pool_size"] == 0

    assert manager.join_pool("a1", pool.id) is True
    assert collector.snapshot()["counters"]["pool_join_total"] == 1
    assert collector.snapshot()["gauges"]["pool_size"] == 1

    manager.leave_pool("a1", pool.id)
    assert collector.snapshot()["counters"]["pool_leave_total"] == 1
    assert collector.snapshot()["gauges"]["pool_size"] == 0
