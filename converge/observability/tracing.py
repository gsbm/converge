import contextlib
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Protocol

# Global context for current trace ID
_current_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)


class SpanExporter(Protocol):
    """Protocol for exporting spans when a trace() context exits."""

    def export(self, span: "Span", duration_sec: float) -> None:
        """Called with the span and its duration in seconds."""
        ...


_span_exporter: ContextVar[SpanExporter | None] = ContextVar("span_exporter", default=None)

def get_current_trace_id() -> str | None:
    """Get the current trace ID from context."""
    return _current_trace_id.get()

def set_trace_id(trace_id: str | None = None) -> None:
    """Set the current trace ID in context. Pass None to clear."""
    _current_trace_id.set(trace_id)


def register_span_exporter(exporter: SpanExporter | None) -> None:
    """Register a span exporter for the current context. When trace() exits, export(span, duration_sec) is called."""
    _span_exporter.set(exporter)

def new_trace_id() -> str:
    """Generate a new trace ID."""
    return str(uuid.uuid4())

@dataclass
class Span:
    """
    Represents a unit of work within a trace.

    Attributes:
        trace_id (str): The global ID of the trace.
        span_id (str): The unique ID of this span.
        parent_id (Optional[str]): The ID of the parent span (if any).
        name (str): The name of the operation being traced.
    """
    trace_id: str
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str | None = None
    name: str = "operation"

    def __enter__(self):
        """Enter the context, setting current trace ID."""
        self._start = time.monotonic()
        self.previous_trace = get_current_trace_id()
        set_trace_id(self.trace_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context, restoring previous trace ID and optionally exporting the span."""
        duration_sec = time.monotonic() - self._start
        exporter = _span_exporter.get()
        if exporter is not None:
            with contextlib.suppress(Exception):
                exporter.export(self, duration_sec)
        if self.previous_trace:
            set_trace_id(self.previous_trace)
        else:
            set_trace_id(None)
        return

def trace(operation_name: str) -> Span:
    """
    Start a new trace span.

    If a trace context already exists, the new span uses the existing trace ID.
    Otherwise, a new trace ID is generated.

    Args:
        operation_name (str): Simple description of the operation.

    Returns:
        Span: A Span object usable as a context manager.
    """
    tid = get_current_trace_id() or new_trace_id()
    return Span(trace_id=tid, name=operation_name)
