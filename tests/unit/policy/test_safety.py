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


def test_executor_safety_action_policy_rejects():
    """StandardExecutor with ActionPolicy skips disallowed decision type."""
    import asyncio
    from unittest.mock import MagicMock

    from converge.coordination.pool_manager import PoolManager
    from converge.coordination.task_manager import TaskManager
    from converge.core.decisions import SendMessage, SubmitTask
    from converge.core.message import Message
    from converge.core.task import Task
    from converge.policy.safety import ActionPolicy
    from converge.runtime.executor import StandardExecutor

    async def run():
        network = MagicMock()
        tm = MagicMock(spec=TaskManager)
        pm = MagicMock(spec=PoolManager)
        policy = ActionPolicy(allowed_actions=["SubmitTask"])
        executor = StandardExecutor("a1", network, tm, pm, safety_policy=(None, policy))
        await executor.execute([SendMessage(message=Message(sender="a1", payload={}))])
        network.send.assert_not_called()
        await executor.execute([SubmitTask(task=Task())])
        tm.submit.assert_called_once()

    asyncio.run(run())


def test_executor_safety_validate_safety_rejects():
    """StandardExecutor with ResourceLimits skips SubmitTask that exceeds limits."""
    import asyncio
    from unittest.mock import MagicMock

    from converge.coordination.pool_manager import PoolManager
    from converge.coordination.task_manager import TaskManager
    from converge.core.decisions import SubmitTask
    from converge.core.task import Task
    from converge.policy.safety import ResourceLimits
    from converge.runtime.executor import StandardExecutor

    async def run():
        tm = MagicMock(spec=TaskManager)
        pm = MagicMock(spec=PoolManager)
        limits = ResourceLimits(max_cpu_tokens=1.0, max_memory_mb=512)
        executor = StandardExecutor("a1", None, tm, pm, safety_policy=(limits, None))
        task = Task(constraints={"cpu": 2.0, "memory_mb": 100})
        await executor.execute([SubmitTask(task=task)])
        tm.submit.assert_not_called()

    asyncio.run(run())
