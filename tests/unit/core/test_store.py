"""Tests for converge.core.store."""

from converge.core.store import Store


def test_store_abstract():
    """Store ABC can be subclassed and basic operations delegated."""

    class MyStore(Store):
        def put(self, k, v):
            super().put(k, v)

        def get(self, k):
            return super().get(k)

        def delete(self, k):
            super().delete(k)

        def list(self, p=""):
            return super().list(p)

    s = MyStore()
    s.put("k", "v")
    assert s.get("k") is None
    s.delete("k")
    assert s.list() is None
