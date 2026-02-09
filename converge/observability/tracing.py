import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field

# Global context for current trace ID
_current_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)

def get_current_trace_id() -> str | None:
    """Get the current trace ID from context."""
    return _current_trace_id.get()

def set_trace_id(trace_id: str | None = None) -> None:
    """Set the current trace ID in context. Pass None to clear."""
    _current_trace_id.set(trace_id)

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
        self.previous_trace = get_current_trace_id()
        set_trace_id(self.trace_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context, restoring previous trace ID."""
        if self.previous_trace:
            set_trace_id(self.previous_trace)
        else:
            set_trace_id(None)

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
