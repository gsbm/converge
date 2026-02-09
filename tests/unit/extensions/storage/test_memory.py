"""Tests for converge.extensions.storage.memory."""

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
