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


def test_format_prometheus():
    mc = MetricsCollector()
    mc.inc("decisions_executed")
    mc.inc("messages_sent", 2)
    mc.gauge("queue_size", 5.0)
    out = mc.format_prometheus()
    assert "decisions_executed" in out
    assert "messages_sent" in out
    assert "queue_size" in out
    assert "counter" in out
    assert "gauge" in out
    assert " 3\n" in out or " 2\n" in out
    assert " 5.0\n" in out
