from abc import ABC, abstractmethod
from typing import Any

from converge.coordination.consensus import Consensus


class GovernanceModel(ABC):
    """
    Abstract base class for pool governance models.
    Determines how decisions are made within a pool (e.g. voting, dictatorial).

    **Implementing a custom governance model**

    Subclass ``GovernanceModel`` and implement ``resolve_dispute(self, context: Any) -> Any``.
    The ``context`` is supplied by the caller when resolving a dispute (e.g. a dict with
    ``"votes"``, ``"chamber_a_votes"``, or any structure your model expects). Return the
    chosen outcome, or ``None`` to indicate no decision / deadlock.

    Example::

        class QualifiedMajorityGovernance(GovernanceModel):
            def __init__(self, threshold: float = 0.66):
                self.threshold = threshold

            def resolve_dispute(self, context: Any) -> Any:
                votes = context.get("votes", []) if isinstance(context, dict) else []
                if not votes:
                    return None
                from collections import Counter
                count = Counter(votes)
                top, n = count.most_common(1)[0]
                return top if n >= len(votes) * self.threshold else None

    Pass an instance when creating a pool (e.g. ``create_pool({"id": "p1", "governance_model": my_model})``)
    or call ``resolve_dispute(context)`` yourself when a dispute arises.
    """

    @abstractmethod
    def resolve_dispute(self, context: Any) -> Any:
        """
        Resolve a dispute or deadlock.

        Args:
            context: Caller-defined data (e.g. dict with "votes", "weights", or
                custom keys). Structure depends on the governance model.

        Returns:
            The chosen outcome, or None if no decision can be made.
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


class BicameralGovernance(GovernanceModel):
    """
    Two chambers must agree (separated powers). Each chamber decides by majority;
    the final outcome is adopted only if both chambers choose the same option.

    Context: dict with "chamber_a_votes" and "chamber_b_votes" (lists of options).
    Optional "tie_breaker" (any): if chambers disagree, return this instead of None.
    """

    def resolve_dispute(self, context: Any) -> Any:
        if not isinstance(context, dict):
            return None
        a_votes = context.get("chamber_a_votes", [])
        b_votes = context.get("chamber_b_votes", [])
        outcome_a = Consensus.majority_vote(a_votes)
        outcome_b = Consensus.majority_vote(b_votes)
        if outcome_a is not None and outcome_a == outcome_b:
            return outcome_a
        return context.get("tie_breaker")


class VetoGovernance(GovernanceModel):
    """
    Counterpower: a designated agent can veto the outcome of a majority vote.
    The body votes; if the veto is not exercised, the majority wins; otherwise
    the decision is blocked (returns None or a fallback).

    Context: "votes" (list), "veto_exercised" (bool), optional "veto_agent_id",
    optional "fallback" when veto is exercised.
    """

    def __init__(self, veto_agent_id: str | None = None):
        self.veto_agent_id = veto_agent_id

    def resolve_dispute(self, context: Any) -> Any:
        if not isinstance(context, dict):
            return None
        if context.get("veto_exercised"):
            return context.get("fallback")
        votes = context.get("votes", [])
        return Consensus.majority_vote(votes)


class EmpiricalGovernance(GovernanceModel):
    """
    Evidence-weighted decision: votes are combined with weights (e.g. confidence
    or evidence strength). The option with the highest total weight wins; ties
    yield None.

    Context: "votes" (list of options), optional "weights" (list of float, same
    length as votes: weight per voter). If "weights" is absent, falls back to
    unweighted majority.
    """

    def resolve_dispute(self, context: Any) -> Any:
        if not isinstance(context, dict):
            return None
        votes = context.get("votes", [])
        weights = context.get("weights")
        if not votes:
            return None
        if weights is None or len(weights) != len(votes):
            return Consensus.majority_vote(votes)
        # Weighted sum per option
        totals: dict[Any, float] = {}
        for option, w in zip(votes, weights):
            totals[option] = totals.get(option, 0.0) + float(w)
        if not totals:
            return None
        best = max(totals.items(), key=lambda x: x[1])
        # Tie: same score as another option
        if sum(1 for v in totals.values() if v == best[1]) > 1:
            return None
        return best[0]
