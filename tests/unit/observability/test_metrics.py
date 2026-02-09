"""Tests for converge.observability.metrics."""

from converge.observability.metrics import MetricsCollector


def test_metrics_collector():
    mc = MetricsCollector()

    mc.inc("requests")
    mc.inc("requests", 2)
    mc.gauge("latency", 0.5)

    snap = mc.snapshot()
    assert snap["counters"]["requests"] == 3
    assert snap["gauges"]["latency"] == 0.5
