from abc import ABC, abstractmethod
from typing import Any


class GovernanceModel(ABC):
    """
    Abstract base class for pool governance models.
    Determines how decisions are made within a pool (e.g. voting, dictatorial).
    """
    @abstractmethod
    def resolve_dispute(self, context: Any) -> Any:
        """
        Resolve a dispute or deadlock.
        """
        pass

class DictatorialGovernance(GovernanceModel):
    """
    A single leader makes all critical decisions.
    """
    def __init__(self, leader_id: str):
        self.leader_id = leader_id

    def resolve_dispute(self, context: Any) -> Any:
        return f"Decided by {self.leader_id}"

class DemocraticGovernance(GovernanceModel):
    """
    Decisions are made by majority vote.
    """
    def resolve_dispute(self, context: Any) -> Any:
        # Placeholder for connection to Consensus module
        return "Decided by vote"
