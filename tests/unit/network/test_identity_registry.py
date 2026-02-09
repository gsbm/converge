"""Tests for converge.network.identity_registry."""

from converge.network.identity_registry import IdentityRegistry


def test_identity_registry_full():
    reg = IdentityRegistry()
    reg.register("agent1", b"pubkey1")
    assert reg.get("agent1") == b"pubkey1"
    assert "agent1" in reg
    reg.unregister("agent1")
    assert reg.get("agent1") is None
    assert "agent1" not in reg
    reg.unregister("nonexistent")
