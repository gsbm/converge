"""Tests for converge.policy.safety."""

from converge.policy.safety import ActionPolicy, ResourceLimits, validate_safety


def test_safety_resource_limits():
    limits = ResourceLimits(max_cpu_tokens=2.0, max_memory_mb=1024)

    assert validate_safety(limits, 1.0, 512)
    assert validate_safety(limits, 2.0, 1024)
    assert not validate_safety(limits, 2.1, 512)
    assert not validate_safety(limits, 1.0, 1025)


def test_action_policy():
    permissive = ActionPolicy()
    assert permissive.is_allowed("any_action")

    restrictive = ActionPolicy(allowed_actions=["read", "write"])
    assert restrictive.is_allowed("read")
    assert restrictive.is_allowed("write")
    assert not restrictive.is_allowed("delete")
    assert not restrictive.is_allowed("execute")
