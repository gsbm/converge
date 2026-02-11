"""Tests for converge.extensions.storage.file."""

from pathlib import Path

from converge.extensions.storage.file import FileStore


def test_file_store_put_get_list_delete(tmp_path):
    store = FileStore(str(tmp_path))

    data = {"a": 1, "b": 2}
    store.put("obj1", data)

    store2 = FileStore(str(tmp_path))
    loaded = store2.get("obj1")
    assert loaded == data

    store.put("obj2", "test")
    keys = store.list()
    assert "obj1" in keys
    assert "obj2" in keys

    store.delete("obj1")
    assert store.get("obj1") is None


def test_file_store_get_nonexistent():
    store = FileStore(str(Path("./nonexistent_dir")))
    assert store.get("none") is None


def test_file_store_get_corrupted(tmp_path):
    store = FileStore(str(tmp_path))
    store.put("corrupt", "data")
    full_path = store._get_path("corrupt")
    with Path(full_path).open("wb") as f:
        f.write(b"not pickle data")

    assert store.get("corrupt") is None


def test_file_store_delete_nonexistent(tmp_path):
    store = FileStore(str(tmp_path))
    store.delete("none")


def test_file_store_list_nonexistent_base(tmp_path):
    fs = FileStore(str(tmp_path / "does_not_exist"))
    assert fs.list() == []


def test_file_store_list_base_not_exists(tmp_path):
    fs = FileStore(str(tmp_path / "nonexistent_subdir"))
    assert fs.list() == []
    assert fs.list("prefix") == []


def test_file_store_list_with_prefix(tmp_path):
    """list(prefix) returns only keys starting with prefix."""
    store = FileStore(str(tmp_path))
    store.put("a1", 1)
    store.put("a2", 2)
    store.put("b1", 3)
    assert set(store.list("a")) == {"a1", "a2"}
    assert store.list("c") == []


def test_file_store_put_if_absent(tmp_path):
    store = FileStore(str(tmp_path))
    assert store.put_if_absent("key1", "a") is True
    assert store.get("key1") == "a"
    assert store.put_if_absent("key1", "b") is False
    assert store.get("key1") == "a"
    assert store.put_if_absent("key2", "c") is True


def test_filestore_additional(tmp_path):
    store = FileStore(str(tmp_path))
    assert store.get("none") is None

    path = tmp_path / "corrupt"
    with path.open("w") as f:
        f.write("not a pickle")
    assert store.get("corrupt") is None

    store.delete("none")
    store.put("exists", 1)
    store.delete("exists")
    assert not (tmp_path / "exists").exists()
