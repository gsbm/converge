"""Tests for converge.observability.coordination_metrics."""

from converge.observability.coordination_metrics import CoordinationMetrics
from converge.observability.metrics import MetricsCollector


def test_coordination_metrics_helpers():
    metrics = MetricsCollector()
    cm = CoordinationMetrics(metrics)
    cm.task_submitted()
    cm.task_claimed()
    cm.task_completed()
    cm.task_failed()
    cm.task_cancelled()
    cm.pool_created()
    cm.pool_join()
    cm.pool_leave()
    cm.pool_size(5)
    cm.pending_tasks(7)

    snap = metrics.snapshot()
    assert snap["counters"]["task_submitted_total"] == 1
    assert snap["counters"]["task_claimed_total"] == 1
    assert snap["counters"]["task_completed_total"] == 1
    assert snap["counters"]["task_failed_total"] == 1
    assert snap["counters"]["task_cancelled_total"] == 1
    assert snap["counters"]["pool_created_total"] == 1
    assert snap["counters"]["pool_join_total"] == 1
    assert snap["counters"]["pool_leave_total"] == 1
    assert snap["gauges"]["pool_size"] == 5
    assert snap["gauges"]["pending_tasks"] == 7
