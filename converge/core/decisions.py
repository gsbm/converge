from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .task import Task

if TYPE_CHECKING:
    from .message import Message

@dataclass
class Decision:
    """Base class for agent decisions."""
    pass

@dataclass
class SendMessage(Decision):
    """Decision to send a single message. Carries the Message to send."""
    message: "Message"

@dataclass
class JoinPool(Decision):
    pool_id: str

@dataclass
class LeavePool(Decision):
    pool_id: str

@dataclass
class CreatePool(Decision):
    spec: dict[str, Any]

@dataclass
class SubmitTask(Decision):
    task: Task

@dataclass
class ClaimTask(Decision):
    task_id: str

@dataclass
class ReportTask(Decision):
    task_id: str
    result: Any
