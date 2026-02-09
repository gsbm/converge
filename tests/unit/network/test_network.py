"""Tests for converge.network.network."""

import asyncio
from unittest.mock import MagicMock

from converge.core.agent import Agent
from converge.core.identity import Identity
from converge.core.message import Message
from converge.network.network import AgentNetwork


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
