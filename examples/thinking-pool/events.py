"""
Structured event timeline and progress rendering for the thinking-pool demo.
Integrates with TaskManager state and optional ReplayLog for user-facing observability.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("thinking_pool.events")


class RequestStage(Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    PARALLEL_EXECUTION = "parallel_execution"
    SYNTHESIS = "synthesis"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TimelineEvent:
    """One entry in the per-request event timeline."""
    ts: float
    kind: str  # e.g. "submitted", "claimed", "reported", "stage"
    task_id: str | None = None
    agent_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


class RequestTracker:
    """
    Tracks lifecycle and events for a single user request (root task + subtasks).
    Used by REPL status/watch/events commands.
    """

    def __init__(self, root_task_id: str):
        self.root_task_id = root_task_id
        self.stage = RequestStage.QUEUED
        self.subtask_ids: list[str] = []
        self.events: list[TimelineEvent] = []
        self.stage_ts: float = time.monotonic()

    def record(self, kind: str, task_id: str | None = None, agent_id: str | None = None, **payload: Any) -> None:
        self.events.append(
            TimelineEvent(
                ts=time.monotonic(),
                kind=kind,
                task_id=task_id,
                agent_id=agent_id,
                payload=payload,
            ),
        )

    def set_stage(self, stage: RequestStage) -> None:
        self.stage = stage
        self.stage_ts = time.monotonic()
        self.record("stage", payload={"stage": stage.value})

    def set_subtasks(self, task_ids: list[str]) -> None:
        self.subtask_ids = list(task_ids)

    def format_events(self, limit: int = 50) -> list[str]:
        """Return a list of human-readable event lines for display."""
        lines = []
        for e in self.events[-limit:]:
            parts = [f"[{e.ts - self.events[0].ts if self.events else 0:.1f}s]", e.kind]
            if e.task_id:
                parts.append(f"task={e.task_id[:8]}...")
            if e.agent_id:
                parts.append(f"agent={e.agent_id[:8]}...")
            if e.payload:
                parts.append(str(e.payload))
            lines.append(" ".join(parts))
        return lines

    def format_events_filtered(self, kind: str | None = None, limit: int = 50) -> list[str]:
        """Like format_events but optionally filter by event kind."""
        events = (
            [e for e in self.events if e.kind == kind][-limit:] if kind else self.events[-limit:]
        )
        lines = []
        for e in events:
            parts = [f"[{e.ts - self.events[0].ts if self.events else 0:.1f}s]", e.kind]
            if e.task_id:
                parts.append(f"task={e.task_id[:8]}...")
            if e.agent_id:
                parts.append(f"agent={e.agent_id[:8]}...")
            if e.payload:
                parts.append(str(e.payload))
            lines.append(" ".join(parts))
        return lines

    def format_summary(self) -> str:
        """One-line summary for status command."""
        return f"root={self.root_task_id[:8]}... stage={self.stage.value} subtasks={len(self.subtask_ids)} events={len(self.events)}"


# Global registry of trackers by root_task_id (demo single-process).
_trackers: dict[str, RequestTracker] = {}


def get_tracker(root_task_id: str) -> RequestTracker:
    if root_task_id not in _trackers:
        _trackers[root_task_id] = RequestTracker(root_task_id)
    return _trackers[root_task_id]


def list_tracked_root_ids() -> list[str]:
    return list(_trackers.keys())


def format_task_status(task: Any) -> str:
    """Format a single task for status display."""
    tid = getattr(task, "id", "?")
    state = getattr(task, "state", None)
    state_val = state.value if state else "?"
    assigned = getattr(task, "assigned_to", None) or "-"
    result_preview = ""
    if getattr(task, "result", None) is not None:
        r = task.result
        if isinstance(r, dict):
            result_preview = str(r)[:80] + "..." if len(str(r)) > 80 else str(r)
        else:
            result_preview = str(r)[:80] + "..." if len(str(r)) > 80 else str(r)
    return f"  {tid[:12]}... state={state_val} assigned_to={assigned[:12] if assigned != '-' else '-'}... result={result_preview[:40] or '-'}"
