"""WebSocket transport for converge."""

import asyncio
import contextlib
import struct

from converge.core.message import Message

from .base import Transport


class WebSocketTransport(Transport):
    """
    WebSocket transport using length-prefixed msgpack framing.
    Requires websockets package (optional dependency).
    """

    def __init__(self, agent_id: str, uri: str):
        """
        Args:
            agent_id: Agent fingerprint.
            uri: WebSocket URI (e.g. ws://localhost:8765).
        """
        self.agent_id = agent_id
        self.uri = uri
        self.inbox: asyncio.Queue = asyncio.Queue()
        self._ws = None
        self._listen_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        try:
            import websockets
        except ImportError:
            raise ImportError("websockets package required: pip install converge[websocket]")

        self._running = True
        self._ws = await websockets.connect(self.uri)
        self._listen_task = asyncio.create_task(self._listen())

    async def stop(self) -> None:
        self._running = False
        if self._listen_task:
            self._listen_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listen_task
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def _listen(self) -> None:
        try:
            import msgpack
        except ImportError:
            raise ImportError("msgpack package required")
        import websockets

        try:
            while self._running and self._ws and not self._ws.closed:
                data = await self._ws.recv()
                if isinstance(data, str):
                    data = data.encode("utf-8")
                if len(data) < 4:
                    continue
                length = struct.unpack("!I", data[:4])[0]
                payload = data[4:4 + length] if length <= len(data) - 4 else data[4:]
                if len(payload) >= length:
                    msg_dict = msgpack.unpackb(payload)
                    msg = Message.from_dict(msg_dict)
                    await self.inbox.put(msg)
        except asyncio.CancelledError:
            pass
        except websockets.exceptions.ConnectionClosed:
            pass

    async def send(self, message: Message) -> None:
        try:
            import msgpack
        except ImportError:
            raise ImportError("msgpack package required")

        if not self._ws or self._ws.closed:
            return
        raw = msgpack.packb(message.to_dict())
        data = raw if raw is not None else b""
        length = len(data)
        frame = struct.pack("!I", length) + data
        await self._ws.send(frame)

    async def receive(self, timeout: float | None = None) -> Message:
        if timeout is not None:
            return await asyncio.wait_for(self.inbox.get(), timeout=timeout)
        return await self.inbox.get()
