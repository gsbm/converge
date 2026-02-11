"""Tests for converge.network.transport.base."""

import asyncio

from converge.network.transport.base import Transport


def test_transport_base_abstract():
    class MyTransport(Transport):
        async def start(self):
            await super().start()

        async def stop(self):
            await super().stop()

        async def send(self, m):
            await super().send(m)

        async def receive(self, timeout=None):
            return await super().receive()

    t = MyTransport()
    asyncio.run(t.start())
    asyncio.run(t.stop())
    asyncio.run(t.send(None))
    assert asyncio.run(t.receive()) is None
