"""
Request orchestration: decompose a user prompt into a root task and capability-scoped subtasks
for parallel execution by the thinking pool.
"""

import logging
from typing import Any

from events import RequestStage, get_tracker
from roles import CAP_CRITIQUE, CAP_RESEARCH, CAP_SYNTHESIZE, CAP_VERIFY

from converge.coordination.task_manager import TaskManager
from converge.core.task import Task

logger = logging.getLogger("thinking_pool.orchestration")

# Default claim TTL so stale claims are released (seconds).
DEFAULT_CLAIM_TTL_SEC = 120.0
# Default timeout for the overall request (used when waiting).
DEFAULT_REQUEST_TIMEOUT_SEC = 180.0


def submit_request(
    task_manager: TaskManager,
    pool_id: str,
    prompt: str,
    *,
    claim_ttl_sec: float = DEFAULT_CLAIM_TTL_SEC,
) -> tuple[str, list[str]]:
    """
    Submit a user request as one root task (for tracking) and multiple subtasks
    with capability routing so different roles can work in parallel.

    Returns:
        (root_task_id, list of subtask_ids)
    """
    # Root task: user-facing request; we use it for wait_until_done and tracking.
    root = Task(
        objective={"prompt": prompt, "type": "root_request"},
        inputs={"prompt": prompt},
        pool_id=pool_id,
        priority=0,
        constraints={"claim_ttl_sec": claim_ttl_sec},
    )
    root_id = task_manager.submit(root)

    tracker = get_tracker(root_id)
    tracker.set_stage(RequestStage.PLANNING)
    tracker.record("submitted", task_id=root_id, payload={"prompt_preview": prompt[:80]})

    # Subtasks: each targets one capability so the right agents see them.
    subtask_specs: list[tuple[str, str, int]] = [
        (CAP_RESEARCH, "research", 10),
        (CAP_CRITIQUE, "critique", 10),
        (CAP_SYNTHESIZE, "synthesis", 8),
        (CAP_VERIFY, "verification", 5),
    ]
    subtask_ids: list[str] = []
    for cap, role_hint, priority in subtask_specs:
        st = Task(
            objective={
                "prompt": prompt,
                "type": "thinking_subtask",
                "role_hint": role_hint,
            },
            inputs={"prompt": prompt, "root_id": root_id},
            pool_id=pool_id,
            priority=priority,
            required_capabilities=[cap],
            constraints={"claim_ttl_sec": claim_ttl_sec},
        )
        st_id = task_manager.submit(st)
        subtask_ids.append(st_id)
        tracker.record("subtask_created", task_id=st_id, payload={"capability": cap})

    tracker.set_subtasks(subtask_ids)
    tracker.set_stage(RequestStage.PARALLEL_EXECUTION)

    logger.info("Submitted request root=%s subtasks=%s", root_id, subtask_ids)
    return root_id, subtask_ids


def get_request_status(
    task_manager: TaskManager,
    root_task_id: str,
) -> dict[str, Any]:
    """
    Return a status dict for the request: root task, subtasks, stage, and summary.
    """
    tracker = get_tracker(root_task_id)
    root = task_manager.get_task(root_task_id)
    subtasks = []
    for sid in tracker.subtask_ids:
        t = task_manager.get_task(sid)
        if t:
            subtasks.append(
                {
                    "id": t.id,
                    "state": t.state.value,
                    "assigned_to": t.assigned_to,
                    "result_preview": str(t.result)[:100] if t.result else None,
                },
            )
    return {
        "root_task_id": root_task_id,
        "stage": tracker.stage.value,
        "root_task": root,
        "subtasks": subtasks,
        "events_count": len(tracker.events),
    }
