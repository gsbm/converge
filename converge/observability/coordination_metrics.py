from __future__ import annotations

from converge.observability.metrics import MetricsCollector


class CoordinationMetrics:
    def __init__(self, collector: MetricsCollector):
        self.collector = collector

    def task_submitted(self) -> None:
        self.collector.inc("task_submitted_total")

    def task_claimed(self) -> None:
        self.collector.inc("task_claimed_total")

    def task_completed(self) -> None:
        self.collector.inc("task_completed_total")

    def task_failed(self) -> None:
        self.collector.inc("task_failed_total")

    def task_cancelled(self) -> None:
        self.collector.inc("task_cancelled_total")

    def pool_created(self) -> None:
        self.collector.inc("pool_created_total")

    def pool_join(self) -> None:
        self.collector.inc("pool_join_total")

    def pool_leave(self) -> None:
        self.collector.inc("pool_leave_total")

    def pool_size(self, size: int) -> None:
        self.collector.gauge("pool_size", float(size))

    def pending_tasks(self, size: int) -> None:
        self.collector.gauge("pending_tasks", float(size))
