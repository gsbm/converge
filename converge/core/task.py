import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .topic import Topic


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
        constraints (Dict[str, Any]): Limitations or requirements. Conventional keys (enforced by
        custom logic if needed): timeout_sec, deadline (iso or unix), claim_ttl_sec (seconds
        after claim before task returns to PENDING if not reported), max_retries, cpu, memory_mb.
        evaluator (str): Identifier for the mechanism to validate results.
        state (TaskState): Current lifecycle state of the task.
        assigned_to (Optional[str]): Fingerprint of the agent assigned to this task.
        result (Optional[Any]): The final output or error descriptor.
        pool_id (Optional[str]): If set, only agents in this pool should see the task (routing).
        topic (Optional[Topic]): If set, used for routing; only agents matching this topic see the task.
        required_capabilities (List[str]): If set, only agents with all these capabilities see the task.
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
    claimed_at: float | None = None  # time.monotonic() when claimed; used for claim_ttl_sec

    # Routing: only agents in the pool or matching topic/capabilities should see this task
    pool_id: str | None = None
    topic: "Topic | None" = None
    required_capabilities: list[str] = field(default_factory=list)
