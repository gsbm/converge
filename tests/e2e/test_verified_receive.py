"""End-to-end test: verified receive with IdentityRegistry."""

import asyncio

import pytest

from converge.core.agent import Agent
from converge.core.identity import Identity
from converge.core.message import Message
from converge.network.identity_registry import IdentityRegistry
from converge.network.transport.local import LocalTransport, LocalTransportRegistry
from converge.runtime.loop import AgentRuntime


class RecordingAgent(Agent):
    def __init__(self, identity):
        super().__init__(identity=identity)
        self.received_messages = []

    def decide(self, messages, tasks):
        self.received_messages.extend(messages)
        return []


@pytest.fixture
def registry():
    reg = LocalTransportRegistry()
    reg.clear()
    return reg


@pytest.mark.asyncio
async def test_e2e_verified_receive_accepts_signed_drops_unverified(registry):
    """B with identity_registry accepts signed message from A; unverified message is dropped."""
    id_a = Identity.generate()
    id_b = Identity.generate()

    # B's registry has A's public key so B can verify A's messages
    registry_b = IdentityRegistry()
    registry_b.register(id_a.fingerprint, id_a.public_key)
    registry_b.register(id_b.fingerprint, id_b.public_key)

    agent_a = Agent(id_a)
    trans_a = LocalTransport(agent_a.id)
    runtime_a = AgentRuntime(agent_a, trans_a)

    agent_b = RecordingAgent(id_b)
    trans_b = LocalTransport(agent_b.id)
    runtime_b = AgentRuntime(agent_b, trans_b, identity_registry=registry_b)

    await runtime_a.start()
    await runtime_b.start()

    # A sends signed message to B
    msg = Message(sender=id_a.fingerprint, recipient=id_b.fingerprint, payload={"signed": True})
    signed = msg.sign(id_a)
    await trans_a.send(signed)

    for _ in range(30):
        await asyncio.sleep(0.08)
        if len(agent_b.received_messages) >= 1:
            break
    assert len(agent_b.received_messages) == 1, (
        f"expected 1 message, got {len(agent_b.received_messages)}"
    )
    assert agent_b.received_messages[0].payload == {"signed": True}

    # Inject unverified message (unknown sender) into B's queue
    unverified = Message(sender="unknown_agent", payload={"fake": True})
    q = registry.get_queue(agent_b.id)
    await q.put(unverified)
    runtime_b.scheduler.notify()
    await asyncio.sleep(0.3)

    # B should still have only one message (unverified dropped)
    assert len(agent_b.received_messages) == 1

    await runtime_a.stop()
    await runtime_b.stop()
