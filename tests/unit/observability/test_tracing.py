"""Tests for converge.observability.tracing."""

from converge.observability.tracing import get_current_trace_id, trace


def test_tracing_context():
    assert get_current_trace_id() is None

    with trace("op1") as span:
        tid = span.trace_id
        assert get_current_trace_id() == tid

        with trace("op2") as span2:
            assert span2.trace_id == tid
            assert get_current_trace_id() == tid

    assert get_current_trace_id() is None
