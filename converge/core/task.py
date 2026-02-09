import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskState(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Task:
    """
    A formally defined unit of work with clear objectives, inputs, and constraints.

    Attributes:
        id (str): Unique identifier for the task.
        objective (Dict[str, Any]): Structural description of the goal.
        inputs (Dict[str, Any]): Data required to execute the task.
        outputs (Optional[Dict[str, Any]]): Resulting data after execution.
        constraints (Dict[str, Any]): Limitations or requirements (e.g. timeout, compute).
        evaluator (str): Identifier for the mechanism to validate results.
        state (TaskState): Current lifecycle state of the task.
        assigned_to (Optional[str]): Fingerprint of the agent assigned to this task.
        result (Optional[Any]): The final output or error descriptor.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    objective: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] | None = None
    constraints: dict[str, Any] = field(default_factory=dict)
    evaluator: str = "default"
    state: TaskState = TaskState.PENDING

    # Optional metadata
    assigned_to: str | None = None
    result: Any | None = None
