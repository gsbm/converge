"""Tests for converge.extensions.storage.versioned."""

from converge.extensions.storage.memory import MemoryStore
from converge.extensions.storage.versioned import SCHEMA_VERSION_KEY, VersionedStore


def test_versioned_store_get_set_version():
    store = MemoryStore()
    versioned = VersionedStore(store)
    assert versioned.get_version() is None
    versioned.set_version(1)
    assert versioned.get_version() == 1
    versioned.set_version(2)
    assert versioned.get_version() == 2


def test_versioned_store_check_version_callback():
    store = MemoryStore()
    seen = []

    def on_change(old, new):
        seen.append((old, new))

    versioned = VersionedStore(store, on_version_change=on_change)
    versioned.set_version(1)
    assert versioned.check_version() == 1
    assert seen == [(None, 1)]

    versioned.set_version(2)
    assert versioned.check_version() == 2
    assert seen == [(None, 1), (1, 2)]

    versioned.check_version()
    assert len(seen) == 2


def test_versioned_store_delegates_put_get_list():
    store = MemoryStore()
    versioned = VersionedStore(store)

    versioned.put("foo", "bar")
    assert versioned.get("foo") == "bar"
    assert store.get("foo") == "bar"

    versioned.put("baz", 42)
    keys = versioned.list("")
    assert "foo" in keys
    assert "baz" in keys

    versioned.delete("foo")
    assert versioned.get("foo") is None


def test_versioned_store_reserved_key():
    store = MemoryStore()
    versioned = VersionedStore(store)
    versioned.set_version("v1")
    assert store.get(SCHEMA_VERSION_KEY) == "v1"
