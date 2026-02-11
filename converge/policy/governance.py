from abc import ABC, abstractmethod
from typing import Any

from converge.coordination.consensus import Consensus


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
        """Return the leader's decision."""
        return f"Decided by {self.leader_id}"


class DemocraticGovernance(GovernanceModel):
    """
    Decisions are made by majority vote using Consensus.majority_vote.
    Expects context to contain a 'votes' key (list of vote options).
    """

    def resolve_dispute(self, context: Any) -> Any:
        """Resolve by majority vote over context['votes']."""
        votes = context.get("votes", []) if isinstance(context, dict) else []
        return Consensus.majority_vote(votes)
