"""Integration tests: storage persistence."""

import shutil
from pathlib import Path

from converge.coordination.pool_manager import PoolManager
from converge.extensions.storage.file import FileStore
from converge.extensions.storage.memory import MemoryStore


def test_memory_store():
    store = MemoryStore()

    store.put("key1", "value1")
    assert store.get("key1") == "value1"

    assert store.get("missing") is None

    store.put("key2", "value2")
    keys = store.list()
    assert "key1" in keys
    assert "key2" in keys

    store.delete("key1")
    assert store.get("key1") is None

    store.delete("nonexistent")

    prefixed = store.list(prefix="key")
    assert "key2" in prefixed


def test_file_store():
    path = Path("./test_data")
    if path.exists():
        shutil.rmtree(path)

    store = FileStore(str(path))

    data = {"a": 1, "b": 2}
    store.put("obj1", data)

    store2 = FileStore(str(path))
    loaded = store2.get("obj1")
    assert loaded == data

    store.put("obj2", "test")
    keys = store.list()
    assert "obj1" in keys
    assert "obj2" in keys

    if path.exists():
        shutil.rmtree(path)


def test_pool_manager_persistence():
    store = MemoryStore()
    pm = PoolManager(store)

    pool = pm.create_pool({"id": "p1"})

    assert store.get("pool:p1") == pool

    pm2 = PoolManager(store)
    pool2 = pm2.get_pool("p1")
    assert pool2 is not None
    assert pool2.id == "p1"


def test_recovery_same_store_restores_pool_and_task_state():
    """Restarting with the same store restores pool and task state (recovery)."""
    from converge.coordination.task_manager import TaskManager
    from converge.core.task import Task

    store = MemoryStore()
    pm = PoolManager(store)
    tm = TaskManager(store)

    pool = pm.create_pool({"id": "recovery-pool"})
    pm.join_pool("agent1", pool.id)
    task = Task(objective={"goal": "test"}, inputs={})
    task_id = tm.submit(task)

    # Simulate restart: new managers with same store
    pm2 = PoolManager(store)
    tm2 = TaskManager(store)

    pool2 = pm2.get_pool("recovery-pool")
    assert pool2 is not None
    assert "agent1" in pool2.agents

    # Task state is in store; get_task loads it
    restored = tm2.get_task(task_id)
    assert restored is not None
    assert restored.objective == {"goal": "test"}


def test_claim_ttl_release_and_reclaim():
    """Claim TTL: after release_expired_claims, task is PENDING again and can be re-claimed."""
    import time

    from converge.coordination.task_manager import TaskManager
    from converge.core.task import Task

    store = MemoryStore()
    tm = TaskManager(store)
    task = Task(objective={"x": 1}, constraints={"claim_ttl_sec": 0.1})
    task_id = tm.submit(task)
    assert tm.claim("agent1", task_id) is True
    time.sleep(0.2)
    released = tm.release_expired_claims(time.monotonic())
    assert released == [task_id]
    assert tm.get_task(task_id).state.value == "pending"
    assert tm.claim("agent2", task_id) is True
    tm.report("agent2", task_id, "done")
    assert tm.get_task(task_id).state.value == "completed"
