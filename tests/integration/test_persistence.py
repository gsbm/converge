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
