"""Tests for converge.network.transport.tcp."""

import asyncio
import struct
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from converge.core.message import Message
from converge.core.topic import Topic
from converge.network.transport.tcp import TcpTransport


@pytest.mark.asyncio
async def test_tcp_handle_client_invalid_msgpack():
    t = TcpTransport("127.0.0.1", 8891, "a1")
    await t.start()
    reader, writer = await asyncio.open_connection("127.0.0.1", 8891)
    writer.write(struct.pack("!I", 5))
    writer.write(b"x" * 5)
    await writer.drain()
    await asyncio.sleep(0.1)
    writer.close()
    await writer.wait_closed()
    await t.stop()


@pytest.mark.asyncio
async def test_tcp_send_no_topic_early_return():
    t = TcpTransport("127.0.0.1", 8887, "a1")
    await t.start()
    msg = Message(sender="a1", payload={}, topics=[])
    await t.send(msg)
    await t.stop()


@pytest.mark.asyncio
async def test_tcp_transport_communication():
    t1 = TcpTransport("127.0.0.1", 8888, "agent1")
    t2 = TcpTransport("127.0.0.1", 8889, "agent2")

    await t1.start()
    await t2.start()

    routing_topic = Topic(namespace="transport.tcp", attributes={"host": "127.0.0.1", "port": 8889})
    msg = Message(sender="agent1", payload={"data": "hello"}, topics=[routing_topic])

    await t1.send(msg)

    received = await asyncio.wait_for(t2.receive(), timeout=1.0)

    assert received.sender == "agent1"
    assert received.payload["data"] == "hello"
    assert any(t.namespace == "transport.tcp" for t in received.topics)

    await t1.stop()
    await t2.stop()


@pytest.mark.asyncio
async def test_tcp_payload_too_large():
    t1 = TcpTransport("127.0.0.1", 9992, "agent1")
    await t1.start()

    reader, writer = await asyncio.open_connection("127.0.0.1", 9992)
    writer.write(struct.pack("!I", 11 * 1024 * 1024))
    await writer.drain()

    await asyncio.sleep(0.1)

    is_closed = False
    try:
        data = await reader.read(1024)
        if not data:
            is_closed = True
    except ConnectionError:
        is_closed = True

    assert is_closed
    writer.close()
    await writer.wait_closed()
    await t1.stop()


@pytest.mark.asyncio
async def test_tcp_send_connection_error():
    t1 = TcpTransport("127.0.0.1", 9993, "a1")

    msg = Message(sender="a1", topics=[Topic("transport.tcp", {"host": "127.0.0.1", "port": 9994})])

    await t1.send(msg)

    await t1.stop()


@pytest.mark.asyncio
async def test_tcp_stop_closes_pool_exception_path():
    t = TcpTransport("127.0.0.1", 8890, "a1")
    await t.start()
    bad_writer = MagicMock()
    bad_writer.close = MagicMock(side_effect=OSError("closed"))
    bad_writer.wait_closed = AsyncMock(return_value=None)
    t.pool[("127.0.0.1", 8891)] = (MagicMock(), bad_writer)
    await t.stop()
    assert len(t.pool) == 0


@pytest.mark.asyncio
async def test_tcp_pooling_reuse():
    t1 = TcpTransport("127.0.0.1", 9995, "agent1")
    t2 = TcpTransport("127.0.0.1", 9996, "agent2")
    await t1.start()
    await t2.start()

    routing = Topic("transport.tcp", {"host": "127.0.0.1", "port": 9996})
    msg = Message(sender="a1", topics=[routing], payload={"x": 1})

    await t1.send(msg)
    await t1.send(msg)

    assert len(t1.pool) == 1

    await t1.stop()
    await t2.stop()


@pytest.mark.asyncio
async def test_tcp_pooling_performance():
    t1 = TcpTransport("127.0.0.1", 9990, "perf1")
    t2 = TcpTransport("127.0.0.1", 9991, "perf2")

    await t1.start()
    await t2.start()

    topic = Topic("transport.tcp", {"host": "127.0.0.1", "port": 9991})
    msg = Message(sender="perf1", topics=[topic], payload={"d": "x" * 1000})

    start = time.time()
    for _ in range(10):
        await t1.send(msg)
        await t2.receive()

    duration = time.time() - start
    assert duration < 2.0

    await t1.stop()
    await t2.stop()


@pytest.mark.asyncio
async def test_tcp_handle_client_garbage():
    t = TcpTransport("127.0.0.1", 9999, "a1")
    await t.start()
    _, writer = await asyncio.open_connection("127.0.0.1", 9999)
    writer.write(b"\xff\xff\xff\xff")
    await writer.drain()
    writer.write(b"\x00\x00\x00\x05garbage")
    await writer.drain()
    await asyncio.sleep(0.1)
    writer.close()
    await writer.wait_closed()
    await t.stop()
