"""Tests for converge.policy.governance."""

from converge.policy.governance import DemocraticGovernance, DictatorialGovernance


def test_governance_models():
    dg = DictatorialGovernance("leader1")
    assert "leader1" in dg.resolve_dispute(None)

    dem = DemocraticGovernance()
    assert dem.resolve_dispute({"votes": ["A", "A", "B"]}) == "A"
    assert dem.resolve_dispute({"votes": []}) is None


def test_governance_abstract():
    from converge.policy.governance import GovernanceModel

    class MyGov(GovernanceModel):
        def resolve_dispute(self, c):
            return super().resolve_dispute(c)

    g = MyGov()
    g.resolve_dispute({})
