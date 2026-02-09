from dataclasses import dataclass


@dataclass
class ResourceLimits:
    """
    Defines upper bounds for resource consumption by an agent or task.

    Attributes:
        max_cpu_tokens (float): Maximum virtual CPU units allowed.
        max_memory_mb (int): Maximum memory in megabytes.
        max_network_requests (int): Maximum network calls per time window.
    """
    max_cpu_tokens: float = 1.0
    max_memory_mb: int = 512
    max_network_requests: int = 100

class ActionPolicy:
    """
    Controls which actions an agent is permitted to execute.

    If 'allowed_actions' is provided, only those actions are allowed (allowlist).
    If 'allowed_actions' is None, all actions are allowed (permissive).
    """
    def __init__(self, allowed_actions: list[str] | None = None):
        """
        Initialize the action policy.

        Args:
            allowed_actions (List[str]): List of allowed action names.
                                       If None, all actions are allowed (permissive).
        """
        self.allowed_actions: set[str] | None = set(allowed_actions) if allowed_actions else None

    def is_allowed(self, action_name: str) -> bool:
        """
        Check if a specific action is authorized.

        Args:
            action_name (str): The name of the action to check.

        Returns:
            bool: True if allowed, False otherwise.
        """
        if self.allowed_actions is None:
            return True
        return action_name in self.allowed_actions

def validate_safety(limits: ResourceLimits, requested_cpu: float, requested_mem: int) -> bool:
    """
    Validate that a resource request is within the defined limits.

    Args:
        limits (ResourceLimits): The active resource constraints.
        requested_cpu (float): The amount of CPU requested.
        requested_mem (int): The amount of memory requested.

    Returns:
        bool: True if within limits, False if exceeded.
    """
    if requested_cpu > limits.max_cpu_tokens:
        return False
    return not requested_mem > limits.max_memory_mb
