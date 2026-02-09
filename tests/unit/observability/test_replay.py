"""Tests for converge.observability.replay."""

from converge.core.message import Message
from converge.observability.replay import ReplayLog


def test_replay_log(tmp_path):
    log = ReplayLog()
    msg = Message(sender="a1", payload={"test": 1})

    log.record_message(msg)
    assert len(log.events) == 1

    path = tmp_path / "replay.json"
    log.export(str(path))

    log2 = ReplayLog()
    log2.load(str(path))
    assert len(log2.events) == 1
    assert log2.events[0]["data"]["id"] == msg.id
