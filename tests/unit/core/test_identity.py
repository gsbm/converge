"""Tests for converge.core.identity."""

import pytest

from converge.core.identity import Identity


def test_identity_creation():
    identity = Identity.generate()
    assert identity.public_key
    assert identity.private_key
    assert identity.fingerprint


def test_identity_from_public_key():
    """Verify-only identity has no private key."""
    full = Identity.generate()
    verify_only = Identity.from_public_key(full.public_key)
    assert verify_only.public_key == full.public_key
    assert verify_only.private_key is None
    assert verify_only.fingerprint == full.fingerprint


def test_identity_repr():
    identity = Identity.generate()
    assert str(identity).startswith("Identity")


def test_identity_immutability():
    """Identity is frozen dataclass."""
    identity = Identity.generate()
    with pytest.raises(Exception):
        identity.fingerprint = "new"
