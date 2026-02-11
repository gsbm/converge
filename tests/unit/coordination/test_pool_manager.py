"""Tests for converge.coordination.pool_manager."""


from converge.coordination.pool_manager import PoolManager
from converge.core.pool import Pool
from converge.core.topic import Topic
from converge.extensions.storage.memory import MemoryStore


def test_pool_manager_flow():
    pm = PoolManager()

    pool = pm.create_pool({"topics": []})
    assert pool.id
    assert pool.id in pm.pools

    agent_id = "agent1"
    success = pm.join_pool(agent_id, pool.id)
    assert success
    assert agent_id in pool.agents

    pm.leave_pool(agent_id, pool.id)
    assert agent_id not in pool.agents

    assert not pm.join_pool(agent_id, "invalid")


def test_pool_manager_join_pool_from_store():
    store = MemoryStore()
    pool = Pool(id="p1", topics=[Topic("ns", {})])
    store.put("pool:p1", pool)

    pm = PoolManager(store=store)
    assert pm.join_pool("agent1", "p1") is True
    assert "agent1" in pool.agents


def test_pool_manager_join_pool_not_found():
    pm = PoolManager(store=MemoryStore())
    assert pm.join_pool("agent1", "nonexistent") is False


def test_pool_manager_leave_pool_from_store():
    store = MemoryStore()
    pool = Pool(id="p1", topics=[Topic("ns", {})])
    pool.add_agent("agent1")
    store.put("pool:p1", pool)

    pm = PoolManager(store=store)
    pm.leave_pool("agent1", "p1")
    assert "agent1" not in pool.agents


def test_pool_manager_create_pool_with_admission_policy():
    class RejectPolicy:
        def can_admit(self, agent_id, context):
            return False

    pm = PoolManager(store=MemoryStore())
    pool = pm.create_pool({"id": "p1", "topics": [Topic("ns", {})]})
    assert pool.id == "p1"

    pm2 = PoolManager(store=MemoryStore())
    pm2.create_pool({
        "id": "p2",
        "topics": [Topic("ns", {})],
        "admission_policy": RejectPolicy(),
    })
    assert pm2.join_pool("agent1", "p2") is False


def test_pool_manager_get_pool_from_store_only():
    store = MemoryStore()
    pm1 = PoolManager(store)
    pm1.create_pool({"id": "p1"})
    pm2 = PoolManager(store)
    assert "p1" not in pm2.pools
    got = pm2.get_pool("p1")
    assert got is not None
    assert got.id == "p1"


def test_pool_manager_get_pool_missing():
    pm = PoolManager()
    assert pm.get_pool("nonexistent") is None


def test_pool_manager_cache_miss_actions():
    store = MemoryStore()

    pm1 = PoolManager(store)
    pool1 = pm1.create_pool({"id": "p1"})
    pm2 = PoolManager(store)
    success = pm2.join_pool("agent1", pool1.id)
    assert success
    assert "agent1" in pm2.get_pool(pool1.id).agents

    pm1.create_pool({"id": "p2"})
    pm1.join_pool("agent1", "p2")
    pm3 = PoolManager(store)
    pm3.leave_pool("agent1", "p2")
    assert "agent1" not in pm3.get_pool("p2").agents


def test_pool_manager_branches():
    pm = PoolManager()
    pm.join_pool("a1", "non-existent")
    pm.leave_pool("a1", "non-existent")


def test_pool_manager_join_with_accepting_policy():
    """Join succeeds when admission policy returns True."""
    class AcceptPolicy:
        def can_admit(self, agent_id, context):
            return True

    pm = PoolManager(store=MemoryStore())
    pm.create_pool({
        "id": "p1",
        "topics": [Topic("ns", {})],
        "admission_policy": AcceptPolicy(),
    })
    assert pm.join_pool("agent1", "p1") is True


def test_pool_manager_join_pool_trust_threshold():
    """join_pool rejects agent when trust_model.get_trust(agent_id) < trust_threshold."""
    from converge.policy.trust import TrustModel

    pm = PoolManager()
    trust = TrustModel()
    trust.update_trust("agent1", 0.3)
    trust.update_trust("agent2", -0.5)
    pool = pm.create_pool({"id": "p1", "trust_model": trust, "trust_threshold": 0.5})
    assert pm.join_pool("agent1", "p1") is True
    assert pm.join_pool("agent2", "p1") is False
    assert "agent2" not in pool.agents


def test_pool_manager_get_pools_for_agent():
    """get_pools_for_agent returns pool IDs the agent has joined."""
    pm = PoolManager()
    p1 = pm.create_pool({"id": "p1"})
    p2 = pm.create_pool({"id": "p2"})
    pm.join_pool("agent1", p1.id)
    pm.join_pool("agent1", p2.id)
    pm.join_pool("agent2", p1.id)

    assert set(pm.get_pools_for_agent("agent1")) == {"p1", "p2"}
    assert pm.get_pools_for_agent("agent2") == ["p1"]
    assert pm.get_pools_for_agent("agent3") == []
