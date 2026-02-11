"""Integration tests for converge run (multi-agent, config)."""

import asyncio

from converge.cli import _create_transport


def test_cli_run_multi_agent_local_in_process():
    """Run the same setup as 'converge run' with agents=2, local transport, pool and discovery."""
    from converge.coordination.pool_manager import PoolManager
    from converge.coordination.task_manager import TaskManager
    from converge.core.agent import Agent
    from converge.core.identity import Identity
    from converge.extensions.storage.memory import MemoryStore
    from converge.network.discovery import DiscoveryService
    from converge.network.network import build_descriptor
    from converge.runtime.loop import AgentRuntime

    store = MemoryStore()
    discovery_service = DiscoveryService(store=store)
    pool_manager = PoolManager(store=MemoryStore())
    task_manager = TaskManager(store=MemoryStore())
    pool = pool_manager.create_pool({"id": "test-pool"})

    runtimes = []
    for i in range(2):
        identity = Identity.generate()
        agent = Agent(identity)
        transport = _create_transport("local", agent.id, "127.0.0.1", 8888)
        agent_descriptor = build_descriptor(agent)
        runtime = AgentRuntime(
            agent=agent,
            transport=transport,
            pool_manager=pool_manager,
            task_manager=task_manager,
            discovery_service=discovery_service,
            agent_descriptor=agent_descriptor,
        )
        runtimes.append(runtime)
        pool_manager.join_pool(agent.id, pool.id)

    async def run_briefly():
        await asyncio.gather(*[r.start() for r in runtimes])
        await asyncio.sleep(0.2)
        for r in runtimes:
            await r.stop()

    asyncio.run(run_briefly())
    assert len(runtimes) == 2
