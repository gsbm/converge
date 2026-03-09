"""Tests for converge.extensions.storage.sqlite_store."""



from converge.extensions.storage.sqlite_store import SQLiteStore


def test_sqlite_store_put_get_delete_list(tmp_path):
    path = tmp_path / "state.db"
    store = SQLiteStore(path)

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


def test_sqlite_store_list_with_prefix(tmp_path):
    path = tmp_path / "state.db"
    store = SQLiteStore(path)
    store.put("task:a", 1)
    store.put("task:b", 2)
    store.put("pool:x", 3)
    assert set(store.list("task")) == {"task:a", "task:b"}
    assert store.list("pool") == ["pool:x"]
    assert store.list("z") == []


def test_sqlite_store_put_if_absent_atomic(tmp_path):
    """Second put_if_absent for same key returns False; value unchanged."""
    path = tmp_path / "state.db"
    store = SQLiteStore(path)
    assert store.put_if_absent("k", "v1") is True
    assert store.get("k") == "v1"
    assert store.put_if_absent("k", "v2") is False
    assert store.get("k") == "v1"
    assert store.put_if_absent("k2", "x") is True


def test_sqlite_store_pickle_objects(tmp_path):
    path = tmp_path / "state.db"
    store = SQLiteStore(path)
    data = {"nested": [1, 2, {"a": True}], "x": 42}
    store.put("obj", data)
    assert store.get("obj") == data
