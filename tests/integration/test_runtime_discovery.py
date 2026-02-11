"""Integration tests for AgentRuntime with DiscoveryService."""


import pytest

from converge.core.agent import Agent
from converge.core.identity import Identity
from converge.core.topic import Topic
from converge.extensions.storage.memory import MemoryStore
from converge.network.discovery import DiscoveryService
from converge.network.transport.local import LocalTransport, LocalTransportRegistry
from converge.runtime.loop import AgentRuntime


@pytest.fixture
def registry():
    """Clear local transport registry for isolated tests."""
    reg = LocalTransportRegistry()
    reg.clear()
    return reg


@pytest.mark.asyncio
async def test_runtime_register_on_start_unregister_on_stop(registry):
    """AgentRuntime with discovery_service registers on start and unregisters on stop."""
    store = MemoryStore()
    discovery = DiscoveryService(store=store)
    identity = Identity.generate()
    agent = Agent(identity)
    agent.topics = [Topic(namespace="test", attributes={})]
    agent.capabilities = ["test_cap"]
    transport = LocalTransport(agent.id)

    runtime = AgentRuntime(
        agent=agent,
        transport=transport,
        discovery_service=discovery,
        agent_descriptor=None,
    )

    assert agent.id not in discovery.descriptors
    await runtime.start()
    assert agent.id in discovery.descriptors
    desc = discovery.descriptors[agent.id]
    assert desc.id == agent.id
    assert len(desc.topics) == 1
    assert desc.topics[0].namespace == "test"
    assert any(c.name == "test_cap" for c in desc.capabilities)

    await runtime.stop()
    assert agent.id not in discovery.descriptors


@pytest.mark.asyncio
async def test_runtime_discovery_with_explicit_descriptor(registry):
    """When agent_descriptor is provided, it is used for registration."""
    from converge.core.capability import Capability
    from converge.network.discovery import AgentDescriptor

    discovery = DiscoveryService()
    identity = Identity.generate()
    agent = Agent(identity)
    transport = LocalTransport(agent.id)
    custom_desc = AgentDescriptor(
        id=agent.id,
        topics=[Topic(namespace="custom_ns", attributes={})],
        capabilities=[Capability("custom", "1.0", "custom desc")],
    )

    runtime = AgentRuntime(
        agent=agent,
        transport=transport,
        discovery_service=discovery,
        agent_descriptor=custom_desc,
    )
    await runtime.start()
    assert discovery.descriptors[agent.id].capabilities[0].name == "custom"
    await runtime.stop()
