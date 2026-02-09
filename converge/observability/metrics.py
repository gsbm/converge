from typing import Any


class MetricsCollector:
    """
    Collects and aggegrates operational metrics.
    """
    def __init__(self):
        self.counters: dict[str, int] = {}
        self.gauges: dict[str, float] = {}

    def inc(self, metric_name: str, value: int = 1) -> None:
        """
        Increment a counter.

        Args:
            metric_name (str): Name of the metric.
            value (int): Amount to increment.
        """
        self.counters[metric_name] = self.counters.get(metric_name, 0) + value

    def gauge(self, metric_name: str, value: float) -> None:
        """
        Set a gauge value.

        Args:
            metric_name (str): Name of the metric.
            value (float): Current value.
        """
        self.gauges[metric_name] = value

    def snapshot(self) -> dict[str, Any]:
        """
        Return a snapshot of all metrics.
        """
        return {
            "counters": self.counters.copy(),
            "gauges": self.gauges.copy(),
        }
