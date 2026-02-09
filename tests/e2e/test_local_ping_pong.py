"""End-to-end test: two agents communicate via local transport."""

import asyncio

import pytest

from converge.core.agent import Agent
from converge.core.identity import Identity
from converge.core.message import Message
from converge.network.transport.local import LocalTransport, LocalTransportRegistry
from converge.runtime.loop import AgentRuntime


class EchoAgent(Agent):
    def decide(self, messages, tasks):
        decisions = []
        for msg in messages:
            if msg.payload.get("content") == "ping":
                reply = Message(
                    sender=self.id,
                    payload={"content": "pong", "reply_to": msg.id},
                )
                decisions.append(reply)
        return decisions


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
async def test_e2e_local_ping_pong(registry):
    id_a = Identity.generate()
    agent_a = RecordingAgent(identity=id_a)
    trans_a = LocalTransport(agent_a.id)
    runtime_a = AgentRuntime(agent=agent_a, transport=trans_a)

    id_b = Identity.generate()
    agent_b = EchoAgent(identity=id_b)
    trans_b = LocalTransport(agent_b.id)
    runtime_b = AgentRuntime(agent=agent_b, transport=trans_b)

    await runtime_a.start()
    await runtime_b.start()

    ping_msg = Message(sender=id_a.fingerprint, payload={"content": "ping"})
    await trans_a.send(ping_msg)

    pong_received = False
    for i in range(20):
        await asyncio.sleep(0.1)
        for m in agent_a.received_messages:
            if m.payload.get("content") == "pong" and m.payload.get("reply_to") == ping_msg.id:
                pong_received = True
                break
        if pong_received:
            break

    assert pong_received

    await runtime_a.stop()
    await runtime_b.stop()
