"""Tests for converge.coordination.delegation."""

from converge.coordination.delegation import DelegationProtocol


def test_delegation_protocol():
    dp = DelegationProtocol()

    did = dp.delegate("a1", "a2", ["scope"])
    assert did in dp.delegations
    assert dp.delegations[did]["active"]

    assert dp.revoke(did)
    assert not dp.delegations[did]["active"]

    assert not dp.revoke("invalid")
