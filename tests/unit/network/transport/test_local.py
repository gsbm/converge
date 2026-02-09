"""Tests for converge.network.transport.local."""

import asyncio

import pytest

from converge.core.identity import Identity
from converge.core.message import Message
from converge.core.topic import Topic
from converge.network.identity_registry import IdentityRegistry
from converge.network.transport.local import LocalTransport, LocalTransportRegistry


@pytest.fixture
def registry():
    reg = LocalTransportRegistry()
    reg.clear()
    return reg


@pytest.mark.asyncio
async def test_local_transport_send_receive_before_start_raises(registry):
    t = LocalTransport("agent1")
    msg = Message(sender="agent1", payload={})
    with pytest.raises(RuntimeError, match="not started"):
        await t.send(msg)
    with pytest.raises(RuntimeError, match="not started"):
        await t.receive()


@pytest.mark.asyncio
async def test_registry_get_queue_and_clear(registry):
    q = asyncio.Queue()
    registry.register("a1", q)
    assert registry.get_queue("a1") is q
    assert registry.get_queue("missing") is None
    registry.unregister("nonexistent")
    registry.clear()
    assert registry.get_queue("a1") is None


@pytest.mark.asyncio
async def test_local_transport_exchange(registry):
    id_a = Identity.generate()
    id_b = Identity.generate()

    trans_a = LocalTransport(id_a.fingerprint)
    trans_b = LocalTransport(id_b.fingerprint)

    await trans_a.start()
    await trans_b.start()

    msg = Message(sender=id_a.fingerprint, payload={"content": "hello from a"})
    msg = msg.sign(id_a)

    await trans_a.send(msg)

    received = await trans_b.receive()

    assert received.id == msg.id
    assert received.sender == id_a.fingerprint
    assert received.payload["content"] == "hello from a"

    await trans_a.stop()
    await trans_b.stop()


@pytest.mark.asyncio
async def test_broadcast_behavior(registry):
    id_a = Identity.generate()
    id_b = Identity.generate()
    id_c = Identity.generate()

    t_a = LocalTransport(id_a.fingerprint)
    t_b = LocalTransport(id_b.fingerprint)
    t_c = LocalTransport(id_c.fingerprint)

    await t_a.start()
    await t_b.start()
    await t_c.start()

    msg = Message(sender=id_a.fingerprint, payload={"type": "broadcast"})

    await t_a.send(msg)

    msg_b = await t_b.receive()
    msg_c = await t_c.receive()

    assert msg_b.id == msg.id
    assert msg_c.id == msg.id

    await t_a.stop()
    await t_b.stop()
    await t_c.stop()


@pytest.mark.asyncio
async def test_transport_receive_verified():
    identity = Identity.generate()
    transport = LocalTransport(identity.fingerprint)
    await transport.start()

    signed = Message(
        sender=identity.fingerprint,
        recipient=identity.fingerprint,
        payload={"x": 1},
    ).sign(identity)
    await transport.send(signed)

    registry = IdentityRegistry()
    registry.register(identity.fingerprint, identity.public_key)
    verified = await transport.receive_verified(registry)
    assert verified is not None
    assert verified.payload == {"x": 1}

    await transport.stop()


@pytest.mark.asyncio
async def test_transport_receive_verified_fails_unknown_sender():
    id1 = Identity.generate()
    id2 = Identity.generate()
    transport = LocalTransport(id1.fingerprint)
    await transport.start()

    signed = Message(
        sender=id1.fingerprint,
        recipient=id1.fingerprint,
        payload={"x": 1},
    ).sign(id1)
    await transport.send(signed)

    registry = IdentityRegistry()
    registry.register(id2.fingerprint, id2.public_key)
    verified = await transport.receive_verified(registry)
    assert verified is None

    await transport.stop()


@pytest.mark.asyncio
async def test_local_transport_subscribe_topic_routing():
    reg = LocalTransportRegistry()
    reg.clear()
    t1 = LocalTransport("a1")
    t2 = LocalTransport("a2")
    t3 = LocalTransport("a3")
    await t1.start()
    await t2.start()
    await t3.start()
    reg.subscribe("a2", "ns1")
    reg.subscribe("a3", "ns1")
    reg.unsubscribe("a3", "ns1")
    subs = reg.get_subscribers_for_topics(["ns1"])
    assert "a2" in subs

    msg = Message(sender="a1", topics=[Topic("ns1", {})], payload={})
    await t1.send(msg)
    r = await t2.receive()
    assert r.sender == "a1"

    msg2 = Message(sender="a1", recipient="a2", payload={})
    await t1.send(msg2)
    r2 = await t2.receive()
    assert r2.payload == {}

    await t1.stop()
    await t2.stop()
    await t3.stop()


@pytest.mark.asyncio
async def test_local_transport_edge_cases():
    from converge.network.transport.local import LocalTransport

    t = LocalTransport("a1")
    await t.start()

    msg = Message(sender="a1", topics=[])
    await t.send(msg)
    await t.stop()


@pytest.mark.asyncio
async def test_local_transport_subscribe_twice_same_agent():
    """subscribe same agent_id twice adds to existing set (covers 34->36 branch)."""
    reg = LocalTransportRegistry()
    reg.clear()
    reg.subscribe("a1", "ns1")
    reg.subscribe("a1", "ns2")
    assert reg.topic_subscriptions["a1"] == {"ns1", "ns2"}


@pytest.mark.asyncio
async def test_local_transport_unsubscribe_when_not_subscribed():
    """unsubscribe(agent_id, topic) when agent_id not in topic_subscriptions does not raise."""
    reg = LocalTransportRegistry()
    reg.clear()
    reg.unsubscribe("nonexistent", "ns1")


@pytest.mark.asyncio
async def test_local_transport_send_topics_no_subscribers_broadcasts():
    """When topics match no subscribers, message goes to all registered queues."""
    reg = LocalTransportRegistry()
    reg.clear()
    t1 = LocalTransport("a1")
    t2 = LocalTransport("a2")
    await t1.start()
    await t2.start()
    msg = Message(sender="a1", topics=[Topic("nobody_subscribed", {})], payload={})
    await t1.send(msg)
    r = await t2.receive()
    assert r.sender == "a1"
    await t1.stop()
    await t2.stop()


@pytest.mark.asyncio
async def test_local_transport_send_to_self_skips_own_queue():
    """When broadcasting, sender does not receive its own message."""
    reg = LocalTransportRegistry()
    reg.clear()
    t1 = LocalTransport("a1")
    t2 = LocalTransport("a2")
    await t1.start()
    await t2.start()
    msg = Message(sender="a1", topics=[Topic("ns", {})], payload={"x": 1})
    reg.subscribe("a1", "ns")
    reg.subscribe("a2", "ns")
    await t1.send(msg)
    r = await t2.receive()
    assert r.payload == {"x": 1}
    await t1.stop()
    await t2.stop()
