"""Tests for converge.observability.replay."""

import asyncio

import pytest

from converge.core.message import Message
from converge.observability.replay import ReplayLog, ReplayRunner
from converge.runtime.loop import Inbox


def test_replay_log(tmp_path):
    log = ReplayLog()
    msg = Message(sender="a1", payload={"test": 1})

    log.record_inbound(msg, agent_id="a1", transport="LocalTransport")
    log.record_outbound(msg, agent_id="a1", transport="LocalTransport")
    log.record_message(msg)
    assert log.events[0]["direction"] == "inbound"
    assert log.events[1]["direction"] == "outbound"
    assert len(log.events) == 3

    path = tmp_path / "replay.json"
    log.export(str(path))

    log2 = ReplayLog()
    log2.load(str(path))
    assert len(log2.events) == 3
    assert log2.events[0]["data"]["id"] == msg.id


def test_replay_runner_dry_run_filters():
    log = ReplayLog()
    m1 = Message(sender="a1", payload={"x": 1}, timestamp=1000)
    m2 = Message(sender="a2", payload={"x": 2}, timestamp=2000)
    log.record_inbound(m1, agent_id="a1", transport="LocalTransport")
    log.record_outbound(m2, agent_id="a2", transport="LocalTransport")
    runner = ReplayRunner(log)
    events = asyncio.run(runner.replay(direction="inbound", agent_id="a1", dry_run=True))
    assert len(events) == 1
    assert events[0]["data"]["id"] == m1.id


@pytest.mark.asyncio
async def test_replay_runner_replays_sorted_into_callback():
    log = ReplayLog()
    later = Message(sender="a1", payload={"x": 2}, timestamp=2000)
    earlier = Message(sender="a1", payload={"x": 1}, timestamp=1000)
    log.record_outbound(later, agent_id="a1", transport="LocalTransport")
    log.record_outbound(earlier, agent_id="a1", transport="LocalTransport")

    seen: list[str] = []

    async def cb(msg: Message) -> None:
        seen.append(msg.id)

    runner = ReplayRunner(log)
    events = await runner.replay(callback=cb)
    assert [e["data"]["id"] for e in events] == [earlier.id, later.id]
    assert seen == [earlier.id, later.id]


@pytest.mark.asyncio
async def test_replay_runner_skips_non_message_events():
    log = ReplayLog()
    log.events.append({"type": "custom", "timestamp": 1000, "data": {"x": 1}})
    msg = Message(sender="a1", payload={"x": 2}, timestamp=1001)
    log.record_outbound(msg, agent_id="a1", transport="LocalTransport")
    runner = ReplayRunner(log)

    events = await runner.replay(dry_run=True)
    assert len(events) == 1
    assert events[0]["data"]["id"] == msg.id


@pytest.mark.asyncio
async def test_replay_runner_replays_into_inbox():
    log = ReplayLog()
    msg = Message(sender="a1", payload={"x": 1}, timestamp=1234)
    log.record_inbound(msg, agent_id="a1", transport="LocalTransport")
    inbox = Inbox()
    runner = ReplayRunner(log)

    await runner.replay(inbox=inbox, direction="inbound")
    polled = inbox.poll()
    assert len(polled) == 1
    assert polled[0].id == msg.id
