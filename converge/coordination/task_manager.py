import time
from typing import Any

from converge.core.store import Store
from converge.core.task import Task, TaskState


class TaskManager:
    """
    Manages the lifecycle of tasks from submission to completion.

    Handles task persistence, assignment (claiming), and result reporting.
    Acts as the source of truth for task state.
    """
    def __init__(self, store: Store | None = None):
        if store is None:
            from converge.extensions.storage.memory import MemoryStore
            store = MemoryStore()
        self.store = store
        self.tasks: dict[str, Task] = {}
        self.pending_task_ids: set[str] = set()

    def submit(self, task: Task) -> str:
        """
        Submit a new task to the system.

        Args:
            task (Task): The Task object to submit.

        Returns:
            str: The unique ID of the submitted task.
        """
        self.tasks[task.id] = task
        self.store.put(f"task:{task.id}", task)
        if task.state == TaskState.PENDING:
            self.pending_task_ids.add(task.id)
        return task.id

    def claim(self, agent_id: str, task_id: str) -> bool:
        """
        Attempt to claim a task for a specific agent.

        A task can only be claimed if it is in the PENDING state.

        Args:
            agent_id (str): The fingerprint of the claiming agent.
            task_id (str): The ID of the task to claim.

        Returns:
            bool: True if claim was successful, False otherwise.
        """
        task = self.tasks.get(task_id)
        if not task:
            task = self.store.get(f"task:{task_id}")
            if task:
                self.tasks[task_id] = task
            else:
                return False

        if task.state != TaskState.PENDING:
            return False

        task.state = TaskState.ASSIGNED
        task.assigned_to = agent_id
        task.claimed_at = time.monotonic()
        self.pending_task_ids.discard(task_id)
        self.store.put(f"task:{task.id}", task)
        return True

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task. Moves it to CANCELLED state.

        Args:
            task_id: The task ID.

        Returns:
            True if the task was found and cancelled, False if not found or not cancellable
            (e.g. already COMPLETED, FAILED, or CANCELLED).
        """
        task = self.tasks.get(task_id)
        if not task:
            task = self.store.get(f"task:{task_id}")
            if task:
                self.tasks[task_id] = task
            else:
                return False
        if task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
            return False
        self.pending_task_ids.discard(task_id)
        task.state = TaskState.CANCELLED
        task.assigned_to = None
        task.claimed_at = None
        self.store.put(f"task:{task.id}", task)
        return True

    def fail_task(
        self,
        task_id: str,
        reason: Any,
        *,
        agent_id: str | None = None,
    ) -> None:
        """
        Mark a task as FAILED with a reason.

        Args:
            task_id: The task ID.
            reason: Error or failure descriptor (stored in task.result).
            agent_id: If set, only the assigned agent can fail the task (same as report).
                If None, any caller can fail (e.g. system-level failure).
        """
        task = self.tasks.get(task_id)
        if not task:
            task = self.store.get(f"task:{task_id}")
            if task:
                self.tasks[task_id] = task
            else:
                return
        if agent_id is not None and task.assigned_to != agent_id:
            raise ValueError(f"Agent {agent_id} not authorized for task {task_id}")
        task.state = TaskState.FAILED
        task.result = reason
        task.claimed_at = None
        self.store.put(f"task:{task.id}", task)

    def release_expired_claims(self, now_ts: float) -> list[str]:
        """
        Release tasks that were claimed but not reported within claim_ttl_sec.
        Moves them back to PENDING and clears assigned_to / claimed_at.

        Call this periodically (e.g. from runtime or a scheduler) with time.monotonic().

        Returns:
            List of task IDs that were released.
        """
        released = []
        ttl_key = "claim_ttl_sec"
        seen_ids = set(self.tasks.keys())
        for key in self.store.list("task:"):
            task_id = key[5:] if key.startswith("task:") else key
            if task_id in seen_ids:
                continue
            seen_ids.add(task_id)
            task = self.store.get(key)
            if not task or task.state != TaskState.ASSIGNED or task.claimed_at is None:
                continue
            self.tasks[task_id] = task
            ttl = task.constraints.get(ttl_key)
            if ttl is None:
                continue
            try:
                ttl_sec = float(ttl)
            except (TypeError, ValueError):
                continue
            if now_ts - task.claimed_at >= ttl_sec:
                task.state = TaskState.PENDING
                task.assigned_to = None
                task.claimed_at = None
                self.pending_task_ids.add(task_id)
                self.store.put(f"task:{task.id}", task)
                released.append(task_id)
        for task_id in list(self.tasks.keys()):
            task = self.tasks[task_id]
            if task.state != TaskState.ASSIGNED or task.claimed_at is None:
                continue
            ttl = task.constraints.get(ttl_key)
            if ttl is None:
                continue
            try:
                ttl_sec = float(ttl)
            except (TypeError, ValueError):
                continue
            if now_ts - task.claimed_at >= ttl_sec:
                task.state = TaskState.PENDING
                task.assigned_to = None
                task.claimed_at = None
                self.pending_task_ids.add(task_id)
                self.store.put(f"task:{task.id}", task)
                released.append(task_id)
        return released

    def report(self, agent_id: str, task_id: str, result: Any) -> None:
        """
        Report the result of a completed task.

        Args:
            agent_id (str): The fingerprint of the agent reporting the result.
            task_id (str): The ID of the completed task.
            result (Any): The result data/object.
        """
        task = self.tasks.get(task_id)
        if not task:
            task = self.store.get(f"task:{task_id}")
            if task:
                self.tasks[task_id] = task
            else:
                return # Or raise

        if task.assigned_to != agent_id:
            raise ValueError(f"Agent {agent_id} not authorized for task {task_id}")

        task.result = result
        task.state = TaskState.COMPLETED
        self.store.put(f"task:{task.id}", task)

    def get_task(self, task_id: str) -> Task | None:
        """
        Retrieve a task by its ID.

        Args:
            task_id (str): The ID of the task.

        Returns:
            Optional[Task]: The Task instance, or None if not found.
        """
        task = self.tasks.get(task_id)
        if not task:
            task = self.store.get(f"task:{task_id}")
            if task:
                self.tasks[task_id] = task
                if task.state == TaskState.PENDING:
                    self.pending_task_ids.add(task_id)
        return task

    def list_pending_tasks(self) -> list[Task]:
        """
        List all tasks currently in the PENDING state.

        Returns:
            List[Task]: A list of pending tasks.
        """
        return [self.tasks[tid] for tid in self.pending_task_ids if tid in self.tasks]

    def list_pending_tasks_for_agent(
        self,
        agent_id: str,
        pool_ids: list[str] | None = None,
        capabilities: list[str] | None = None,
    ) -> list[Task]:
        """
        List pending tasks visible to an agent given its pool membership and capabilities.

        Tasks are filtered so that: if a task has pool_id set, the agent must be in that
        pool (pool_id in pool_ids); if a task has required_capabilities, the agent must
        have all of them (required_capabilities subset of capabilities). When pool_ids
        or capabilities is None, that filter is not applied (backward compatible).

        Args:
            agent_id (str): The agent fingerprint (used for consistency; filtering is by
                pool_ids and capabilities).
            pool_ids (List[str] | None): Pool IDs the agent has joined. If None, pool_id
                filter is not applied.
            capabilities (List[str] | None): Capability names the agent has. If None,
                required_capabilities filter is not applied.

        Returns:
            List[Task]: Pending tasks that the agent is allowed to see.
        """
        pending = self.list_pending_tasks()
        result = []
        agent_cap_set = set(capabilities) if capabilities is not None else None
        agent_pool_set = set(pool_ids) if pool_ids is not None else None
        for task in pending:
            if (
                task.pool_id is not None
                and agent_pool_set is not None
                and task.pool_id not in agent_pool_set
            ):
                continue
            if (
                task.required_capabilities
                and agent_cap_set is not None
                and not set(task.required_capabilities).issubset(agent_cap_set)
            ):
                continue
            result.append(task)
        return result
