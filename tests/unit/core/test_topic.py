"""Tests for converge.core.topic."""

from converge.core.topic import Topic


def test_topic_to_dict_from_dict():
    """Topic.to_dict and from_dict round-trip."""
    t = Topic(namespace="ns", attributes={"a": 1, "b": 2}, version="2.0")
    d = t.to_dict()
    assert d["namespace"] == "ns"
    assert d["attributes"] == {"a": 1, "b": 2}
    assert d["version"] == "2.0"
    t2 = Topic.from_dict(d)
    assert t2.namespace == t.namespace
    assert t2.attributes == t.attributes
    assert str(t2) == str(t)


def test_topic_formatting():
    t = Topic("ns", {"a": 1})
    s = str(t)
    assert "ns" in s
    assert "a=1" in s
