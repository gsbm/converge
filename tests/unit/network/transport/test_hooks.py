"""Tests for converge.network.transport.hooks."""

import asyncio

import pytest

from converge.core.message import Message
from converge.network.transport.hooks import HookedTransport
from converge.network.transport.local import LocalTransport, LocalTransportRegistry


@pytest.fixture
def registry():
    reg = LocalTransportRegistry()
    reg.clear()
    return reg


class RecordingHook:
    def __init__(self):
        self.calls: list[str] = []
        self.errors: list[tuple[str, str]] = []

    def pre_send(self, message: Message) -> Message | None:
        self.calls.append(f"pre:{message.id}")
        message.payload["hooked"] = True
        return message

    def post_receive(self, message: Message) -> Message | None:
        self.calls.append(f"post:{message.id}")
        return message

    def on_error(self, stage: str, error: Exception, _context: dict) -> None:
        self.errors.append((stage, str(error)))


@pytest.mark.asyncio
async def test_hooked_transport_pre_and_post_chain(registry):
    a = LocalTransport("a")
    b = LocalTransport("b")
    hook = RecordingHook()
    ta = HookedTransport(a, hooks=[hook])
    tb = HookedTransport(b, hooks=[hook])
    await ta.start()
    await tb.start()
    try:
        msg = Message(sender="a", recipient="b", payload={})
        await ta.send(msg)
        got = await asyncio.wait_for(tb.receive(timeout=0.2), timeout=0.5)
        assert got.payload["hooked"] is True
        assert any(c.startswith("pre:") for c in hook.calls)
        assert any(c.startswith("post:") for c in hook.calls)
    finally:
        await ta.stop()
        await tb.stop()


class DropIngressHook:
    def pre_send(self, message: Message) -> Message | None:
        return message

    def post_receive(self, message: Message) -> Message | None:
        _ = message
        return None


@pytest.mark.asyncio
async def test_hooked_transport_drop_on_post_receive(registry):
    a = LocalTransport("a")
    b = LocalTransport("b")
    ta = HookedTransport(a, hooks=[DropIngressHook()])
    tb = HookedTransport(b, hooks=[DropIngressHook()])
    await ta.start()
    await tb.start()
    try:
        await ta.send(Message(sender="a", recipient="b", payload={}))
        with pytest.raises(TimeoutError, match="dropped by post_receive hook"):
            await tb.receive(timeout=0.2)
    finally:
        await ta.stop()
        await tb.stop()


class ErrorHook:
    def __init__(self):
        self.errors: list[str] = []

    def pre_send(self, message: Message) -> Message | None:
        raise ValueError("boom")

    def post_receive(self, message: Message) -> Message | None:
        return message

    def on_error(self, stage: str, error: Exception, _context: dict) -> None:
        self.errors.append(f"{stage}:{error}")


@pytest.mark.asyncio
async def test_hooked_transport_on_error_called(registry):
    a = LocalTransport("a")
    hook = ErrorHook()
    ta = HookedTransport(a, hooks=[hook])
    await ta.start()
    try:
        with pytest.raises(ValueError, match="boom"):
            await ta.send(Message(sender="a", payload={}))
        assert hook.errors and hook.errors[0].startswith("pre_send:")
    finally:
        await ta.stop()
