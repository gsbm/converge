"""Tests for converge.network.network."""

import asyncio
from unittest.mock import MagicMock

from converge.core.agent import Agent
from converge.core.capability import Capability
from converge.core.identity import Identity
from converge.core.message import Message
from converge.core.topic import Topic
from converge.network.discovery import AgentDescriptor
from converge.network.network import AgentNetwork, build_descriptor


class MockTransport:
    def __init__(self):
        self.sent_count = 0

    async def send(self, message):
        self.sent_count += 1

    async def receive(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass


def test_network_register_unregister():
    mock_transport = MockTransport()
    net = AgentNetwork(transport=mock_transport)

    agent = Agent(Identity.generate())
    net.register_agent(agent)
    assert agent.id in net.local_agents

    net.unregister_agent(agent.id)
    assert agent.id not in net.local_agents


def test_network_send_broadcast_delegates_to_transport():
    mock_transport = MockTransport()
    net = AgentNetwork(transport=mock_transport)

    agent = Agent(Identity.generate())
    net.register_agent(agent)

    msg = Message(sender="a", payload="p")
    asyncio.run(net.send(msg))
    assert mock_transport.sent_count == 1

    asyncio.run(net.broadcast(msg))
    assert mock_transport.sent_count == 2


def test_network_unregister_branch():
    net = AgentNetwork(MagicMock())
    net.unregister_agent("non-existent")


def test_build_descriptor_from_agent():
    """build_descriptor produces AgentDescriptor with id, topics, capabilities."""
    identity = Identity.generate()
    agent = Agent(identity)
    agent.topics = [Topic(namespace="ns1", attributes={})]
    agent.capabilities = ["cap_a", "cap_b"]

    desc = build_descriptor(agent)
    assert isinstance(desc, AgentDescriptor)
    assert desc.id == agent.id
    assert len(desc.topics) == 1
    assert desc.topics[0].namespace == "ns1"
    assert len(desc.capabilities) == 2
    assert desc.capabilities[0].name == "cap_a"
    assert desc.capabilities[1].name == "cap_b"


def test_build_descriptor_with_capability_objects():
    """build_descriptor accepts Capability objects in agent.capabilities."""
    identity = Identity.generate()
    agent = Agent(identity)
    agent.capabilities = [Capability("x", "2.0", "desc")]

    desc = build_descriptor(agent)
    assert len(desc.capabilities) == 1
    assert desc.capabilities[0].name == "x"
    assert desc.capabilities[0].version == "2.0"
