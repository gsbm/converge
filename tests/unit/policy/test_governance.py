"""Tests for converge.policy.governance."""

from converge.policy.governance import (
    BicameralGovernance,
    DemocraticGovernance,
    DictatorialGovernance,
    EmpiricalGovernance,
    VetoGovernance,
)


def test_governance_models():
    dg = DictatorialGovernance("leader1")
    assert "leader1" in dg.resolve_dispute(None)

    dem = DemocraticGovernance()
    assert dem.resolve_dispute({"votes": ["A", "A", "B"]}) == "A"
    assert dem.resolve_dispute({"votes": []}) is None


def test_bicameral_governance():
    bic = BicameralGovernance()
    # Both chambers agree on A
    assert bic.resolve_dispute({"chamber_a_votes": ["A", "A", "B"], "chamber_b_votes": ["A", "A", "B"]}) == "A"
    # Chambers disagree: no majority in one or different outcomes
    assert bic.resolve_dispute({"chamber_a_votes": ["A", "A", "B"], "chamber_b_votes": ["B", "B", "A"]}) is None
    # Tie-breaker when disagree
    assert bic.resolve_dispute({
        "chamber_a_votes": ["A", "A"],
        "chamber_b_votes": ["B", "B"],
        "tie_breaker": "default",
    }) == "default"


def test_veto_governance():
    veto = VetoGovernance(veto_agent_id="overseer")
    assert veto.resolve_dispute({"votes": ["A", "A", "B"]}) == "A"
    assert veto.resolve_dispute({"votes": ["A", "A", "B"], "veto_exercised": True}) is None
    assert veto.resolve_dispute({"votes": ["A", "A", "B"], "veto_exercised": True, "fallback": "blocked"}) == "blocked"


def test_empirical_governance():
    emp = EmpiricalGovernance()
    # Unweighted fallback
    assert emp.resolve_dispute({"votes": ["A", "A", "B"]}) == "A"
    # Weighted: B has higher total (0.9 + 0.8) than A (0.5)
    assert emp.resolve_dispute({"votes": ["A", "B", "B"], "weights": [0.5, 0.9, 0.8]}) == "B"
    # Tie in weights
    assert emp.resolve_dispute({"votes": ["A", "B"], "weights": [1.0, 1.0]}) is None


def test_governance_abstract():
    from converge.policy.governance import GovernanceModel

    class MyGov(GovernanceModel):
        def resolve_dispute(self, c):
            return super().resolve_dispute(c)

    g = MyGov()
    g.resolve_dispute({})


def test_custom_governance_model():
    """Custom governance: subclass GovernanceModel and implement resolve_dispute."""
    from converge.policy.governance import GovernanceModel

    class QualifiedMajorityGovernance(GovernanceModel):
        def __init__(self, threshold: float = 0.66):
            self.threshold = threshold

        def resolve_dispute(self, context):
            if not isinstance(context, dict):
                return None
            votes = context.get("votes", [])
            if not votes:
                return None
            from collections import Counter
            count = Counter(votes)
            top, n = count.most_common(1)[0]
            return top if n >= len(votes) * self.threshold else None

    q = QualifiedMajorityGovernance(threshold=0.66)
    assert q.resolve_dispute({"votes": ["A", "A", "B"]}) == "A"  # 2/3
    assert q.resolve_dispute({"votes": ["A", "B", "C"]}) is None  # no 66%
    # Can be passed to create_pool and stored on pool.governance_model
    from converge.coordination.pool_manager import PoolManager
    from converge.extensions.storage.memory import MemoryStore
    pm = PoolManager(store=MemoryStore())
    pool = pm.create_pool({"id": "custom-pool", "governance_model": q})
    assert pool.governance_model is q
    assert pool.governance_model.resolve_dispute({"votes": ["X", "X", "Y"]}) == "X"
