import uuid
from dataclasses import dataclass, field
from typing import Any

from .topic import Topic


@dataclass
class Pool:
    """
    A scoped sub-network of agents organizing around shared topics or goals.

    Attributes:
        id (str): Unique identifier for the pool.
        topics (List[Topic]): Topics associated with this pool.
        admission_policy (Dict[str, Any]): Rules for agent admission.
        governance (Dict[str, Any]): Rules for decision making within the pool.
        agents (Set[str]): Set of AgentIDs (fingerprints) currently in the pool.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topics: list[Topic] = field(default_factory=list)
    admission_policy: dict[str, Any] = field(default_factory=dict)
    admission_policy_instance: Any = field(default=None, repr=False)
    governance: dict[str, Any] = field(default_factory=dict)
    agents: set[str] = field(default_factory=set)
    trust_model: Any = field(default=None, repr=False)
    trust_threshold: float = 0.0

    def add_agent(self, agent_id: str) -> None:
        """Add an agent to the pool."""
        self.agents.add(agent_id)

    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent from the pool."""
        self.agents.discard(agent_id)
