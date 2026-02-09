"""Tests for converge.core.capability."""

from converge.core.capability import Capability, CapabilitySet


def test_capability_repr():
    c = Capability("compute", "1.0", "compute capability")
    cs = CapabilitySet([c])
    assert "Capability" in repr(c)
    assert "CapabilitySet" in repr(cs)
    cs.add(Capability("analyze", "1.0", "analyze"))
    assert cs.has("compute")
    assert cs.has("analyze")
    assert not cs.has("other")


def test_capability_defaults():
    cap = Capability(name="test", version="1.0", description="test cap")
    assert cap.constraints == {}
    assert cap.costs == {}
