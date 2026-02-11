"""Tests for converge.network.discovery."""

from converge.core.agent import Agent
from converge.core.capability import Capability
from converge.core.identity import Identity
from converge.core.topic import Topic
from converge.network.discovery import (
    AgentDescriptor,
    DiscoveryQuery,
    DiscoveryService,
)
from converge.network.network import AgentNetwork


class DiscoverableAgent(Agent):
    def __init__(self, identity, topics=None, capabilities=None):
        super().__init__(identity)
        self.topics = topics or []
        self.capabilities = capabilities or []


class MockTransport:
    async def send(self, m):
        pass

    async def receive(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass


def test_discovery_filtering():
    t1 = Topic(namespace="science", attributes={"field": "bio"})
    t2 = Topic(namespace="finance", attributes={"field": "crypto"})

    c1 = Capability(name="compute", version="1.0", description="gpu")
    c2 = Capability(name="analyze", version="1.0", description="nlp")

    a1 = DiscoverableAgent(Identity.generate(), topics=[t1], capabilities=[c1])
    a2 = DiscoverableAgent(Identity.generate(), topics=[t2], capabilities=[c2])
    a3 = DiscoverableAgent(Identity.generate(), topics=[t1, t2], capabilities=[c1, c2])

    net = AgentNetwork(transport=MockTransport())
    net.register_agent(a1)
    net.register_agent(a2)
    net.register_agent(a3)

    q1 = DiscoveryQuery(topics=[t1])
    res1 = net.discover(q1)
    ids1 = {d.id for d in res1}
    assert a1.id in ids1
    assert a3.id in ids1
    assert a2.id not in ids1

    q2 = DiscoveryQuery(capabilities=["analyze"])
    res2 = net.discover(q2)
    ids2 = {d.id for d in res2}
    assert a2.id in ids2
    assert a3.id in ids2
    assert a1.id not in ids2

    q3 = DiscoveryQuery(topics=[t1], capabilities=["analyze"])
    res3 = net.discover(q3)
    ids3 = {d.id for d in res3}
    assert a3.id in ids3
    assert a1.id not in ids3
    assert a2.id not in ids3


def test_discovery_service_registry():
    ds = DiscoveryService()
    desc = AgentDescriptor("id1", [], [])
    ds.register(desc)
    assert "id1" in ds.descriptors
    ds.unregister("id1")
    assert "id1" not in ds.descriptors
    ds.unregister("id2")


def test_agent_descriptor_to_dict_from_dict():
    cap = Capability("compute", "1.0", "desc", latency_ms=100)
    desc = AgentDescriptor("id1", [Topic("ns", {})], [cap])
    d = desc.to_dict()
    assert d["id"] == "id1"
    assert "public_key" not in d
    restored = AgentDescriptor.from_dict(d)
    assert restored.id == desc.id
    assert len(restored.capabilities) == 1
    assert restored.capabilities[0].name == "compute"
    assert restored.public_key is None


def test_agent_descriptor_public_key_roundtrip():
    """AgentDescriptor with public_key serializes and deserializes correctly."""
    import base64
    cap = Capability("c", "1.0", "d")
    key_bytes = b"x" * 32
    desc = AgentDescriptor("id1", [Topic("ns", {})], [cap], public_key=key_bytes)
    d = desc.to_dict()
    assert "public_key" in d
    assert base64.b64decode(d["public_key"].encode("ascii")) == key_bytes
    restored = AgentDescriptor.from_dict(d)
    assert restored.public_key == key_bytes


def test_discovery_service_load_from_store_invalid_skipped():
    from converge.extensions.storage.memory import MemoryStore

    store = MemoryStore()
    store.put("discovery:agent:bad", {"id": "bad", "topics": "invalid"})
    ds = DiscoveryService(store=store)
    assert "bad" not in ds.descriptors


def test_discovery_service_with_store():
    from converge.extensions.storage.memory import MemoryStore

    store = MemoryStore()
    cap = Capability("compute", "1.0", "desc")
    desc = AgentDescriptor("id1", [Topic("ns", {})], [cap])
    store.put("discovery:agent:id1", desc.to_dict())

    ds = DiscoveryService(store=store)
    assert "id1" in ds.descriptors
    ds.unregister("id1")
    assert "id1" not in ds.descriptors


def test_discovery_query_topics_capabilities():
    cap = Capability("compute", "1.0", "desc")
    desc1 = AgentDescriptor("id1", [Topic("ns1", {})], [cap])
    desc2 = AgentDescriptor("id2", [Topic("ns2", {})], [])
    ds = DiscoveryService()
    ds.register(desc1)
    ds.register(desc2)

    results = ds.query(DiscoveryQuery(topics=[Topic("ns1", {})]), [desc1, desc2])
    assert len(results) == 1
    assert results[0].id == "id1"

    results2 = ds.query(DiscoveryQuery(capabilities=["compute"]), [desc1, desc2])
    assert len(results2) == 1
    assert results2[0].id == "id1"


def test_discovery_register_then_query_returns_agent():
    """After register(), query() with service descriptors returns the agent."""
    cap = Capability("c", "1.0", "d")
    desc = AgentDescriptor("id1", [Topic("ns", {})], [cap])
    ds = DiscoveryService()
    ds.register(desc)
    candidates = list(ds.descriptors.values())
    results = ds.query(DiscoveryQuery(), candidates)
    assert len(results) == 1
    assert results[0].id == "id1"


def test_discovery_unregister_then_query_omits_agent():
    """After unregister(), the agent is no longer in descriptors so query omits it."""
    cap = Capability("c", "1.0", "d")
    desc1 = AgentDescriptor("id1", [Topic("ns1", {})], [cap])
    desc2 = AgentDescriptor("id2", [Topic("ns2", {})], [cap])
    ds = DiscoveryService()
    ds.register(desc1)
    ds.register(desc2)
    candidates_before = list(ds.descriptors.values())
    assert len(candidates_before) == 2
    ds.unregister("id1")
    candidates_after = list(ds.descriptors.values())
    assert len(candidates_after) == 1
    assert candidates_after[0].id == "id2"


def test_discovery_register_persists_to_store():
    """register() with store calls store.put (covers line 90)."""
    from converge.extensions.storage.memory import MemoryStore

    store = MemoryStore()
    ds = DiscoveryService(store=store)
    cap = Capability("c", "1.0", "d")
    desc = AgentDescriptor("id1", [Topic("ns", {})], [cap])
    ds.register(desc)
    assert store.get("discovery:agent:id1") is not None


def test_discovery_load_from_store_with_keys():
    """_load_from_store iterates keys from store.list (covers line 76)."""
    from converge.extensions.storage.memory import MemoryStore

    store = MemoryStore()
    cap = Capability("c", "1.0", "d")
    desc = AgentDescriptor("id1", [Topic("ns", {})], [cap])
    store.put("discovery:agent:id1", desc.to_dict())
    ds = DiscoveryService(store=store)
    assert "id1" in ds.descriptors


def test_discovery_load_from_store_invalid_entry_skipped():
    """_load_from_store skips entry when from_dict raises (covers 80->78)."""
    from converge.extensions.storage.memory import MemoryStore

    store = MemoryStore()
    store.put("discovery:agent:bad", {"id": "bad", "topics": "not a list"})
    ds = DiscoveryService(store=store)
    assert "bad" not in ds.descriptors
