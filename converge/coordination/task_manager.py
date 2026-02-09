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
        self.pending_task_ids.discard(task_id)
        self.store.put(f"task:{task.id}", task)
        return True

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
