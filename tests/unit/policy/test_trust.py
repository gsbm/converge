"""Tests for converge.policy.trust."""

from converge.policy.trust import TrustModel


def test_trust_model():
    tm = TrustModel()
    agent_id = "a1"

    assert tm.get_trust(agent_id) == 0.5

    assert tm.update_trust(agent_id, 0.1) == 0.6
    assert tm.get_trust(agent_id) == 0.6

    tm.update_trust(agent_id, 1.0)
    assert tm.get_trust(agent_id) == 1.0

    tm.update_trust(agent_id, -2.0)
    assert tm.get_trust(agent_id) == 0.0
