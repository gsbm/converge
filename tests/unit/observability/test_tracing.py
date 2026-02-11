"""Tests for converge.observability.tracing."""

from converge.observability.tracing import get_current_trace_id, register_span_exporter, trace


def test_tracing_context():
    assert get_current_trace_id() is None

    with trace("op1") as span:
        tid = span.trace_id
        assert get_current_trace_id() == tid

        with trace("op2") as span2:
            assert span2.trace_id == tid
            assert get_current_trace_id() == tid

    assert get_current_trace_id() is None


def test_span_exporter_invoked():
    """When a span exporter is registered, it is called with span and duration on context exit."""
    exported = []

    class CapturingExporter:
        def export(self, span, duration_sec):
            exported.append((span.name, duration_sec))

    register_span_exporter(CapturingExporter())
    try:
        with trace("test_op") as span:
            assert span.name == "test_op"
        assert len(exported) == 1
        assert exported[0][0] == "test_op"
        assert exported[0][1] >= 0
    finally:
        register_span_exporter(None)
