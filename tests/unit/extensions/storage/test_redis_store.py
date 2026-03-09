"""Tests for converge.extensions.storage.redis_store."""

import pytest

pytest.importorskip("redis")
pytest.importorskip("fakeredis")

import fakeredis

from converge.extensions.storage.redis_store import RedisStore


@pytest.fixture
def redis_store():
    client = fakeredis.FakeRedis(decode_responses=False)
    store = RedisStore(client=client)
    yield store


def test_redis_store_put_get_delete_list(redis_store):
    redis_store.put("key1", "value1")
    assert redis_store.get("key1") == "value1"

    assert redis_store.get("missing") is None

    redis_store.put("key2", "value2")
    keys = redis_store.list()
    assert "key1" in keys
    assert "key2" in keys

    redis_store.delete("key1")
    assert redis_store.get("key1") is None

    redis_store.delete("nonexistent")


def test_redis_store_list_with_prefix(redis_store):
    redis_store.put("task:a", 1)
    redis_store.put("task:b", 2)
    redis_store.put("pool:x", 3)
    assert set(redis_store.list("task")) == {"task:a", "task:b"}
    assert redis_store.list("pool") == ["pool:x"]
    assert redis_store.list("z") == []


def test_redis_store_put_if_absent_atomic(redis_store):
    """Second put_if_absent for same key returns False; value unchanged."""
    assert redis_store.put_if_absent("k", "v1") is True
    assert redis_store.get("k") == "v1"
    assert redis_store.put_if_absent("k", "v2") is False
    assert redis_store.get("k") == "v1"
    assert redis_store.put_if_absent("k2", "x") is True
