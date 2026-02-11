import asyncio
import contextlib
import ssl
import struct

from converge.core.message import Message

from .base import Transport


class TcpTransport(Transport):
    """
    TCP Transport using asyncio.
    Uses length-prefixed framing: [4 bytes length][payload].
    Supports optional TLS via ssl_context.
    """
    def __init__(
        self,
        host: str,
        port: int,
        identity_fingerprint: str,
        *,
        ssl_context: ssl.SSLContext | None = None,
    ):
        self.host = host
        self.port = port
        self.fingerprint = identity_fingerprint
        self.ssl_context = ssl_context
        self.server: asyncio.AbstractServer | None = None
        self.inbox: asyncio.Queue = asyncio.Queue()
        # Connection pool: (host, port) -> (reader, writer, lock)
        self.pool: dict[tuple, tuple] = {}

    async def start(self) -> None:
        self.server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port,
            ssl=self.ssl_context,
        )

    async def stop(self) -> None:
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        # Close pooled connections
        for (_h, _p), entry in self.pool.items():
            _r, w = entry[0], entry[1]
            try:
                w.close()
                await w.wait_closed()
            except Exception:
                pass
        self.pool.clear()

    async def _handle_client(self, reader, writer):
        try:
            # Read loop
            while True:
                # Read length prefix
                data = await reader.read(4)
                if not data:
                    break

                length = struct.unpack('!I', data)[0]

                # Check reasonable length to avoid OOM attacks
                if length > 10 * 1024 * 1024: # 10MB limit
                    # logger.warning("Payload too large")
                    break

                # Read payload
                payload_data = await reader.readexactly(length)

                # Deserialize using msgpack
                import msgpack
                msg_dict = msgpack.unpackb(payload_data)

                # Reconstruct Message object
                msg = Message.from_dict(msg_dict)

                if isinstance(msg, Message):
                    await self.inbox.put(msg)

        except asyncio.IncompleteReadError:
            pass
        except Exception:
            # print(f"Error handling client: {e}")
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    async def _get_connection(self, host: str, port: int):
        key = (host, port)
        if key in self.pool:
            entry = self.pool[key]
            reader, writer, lock = entry[0], entry[1], entry[2]
            if not writer.is_closing():
                return reader, writer, lock
            del self.pool[key]

        reader, writer = await asyncio.open_connection(
            host,
            port,
            ssl=self.ssl_context,
        )
        lock = asyncio.Lock()
        self.pool[key] = (reader, writer, lock)
        return reader, writer, lock

    async def send(self, message: Message) -> None:
        # Determine destination from topics
        target_host = None
        target_port = None

        for topic in message.topics:
            if topic.namespace == "transport.tcp":
                target_host = topic.attributes.get("host")
                target_port = topic.attributes.get("port")
                break

        if not target_host or not target_port:
             return

        try:
            # Use pooled connection
            # Note: For strict robust pooling we need to handle concurrency (lock per connection)
            # or use a queue per connection. For this iteration, simple reuse is a step up.
            # Assuming sequential sends for simplicity or relying on asyncio stream safety (partial).
            # But await write/drain is not atomic on the socket.
            # Ideally we'd lock. Let's add a lock implicitly by not reusing concurrently?
            # Or just assume low contention for now.
            # Proper way: (reader, writer) = await self._get_connection(...)

            _reader, writer, lock = await self._get_connection(target_host, target_port)

            # Serialize using msgpack
            import msgpack
            data = msgpack.packb(message.to_dict())
            if data is None:
                data = b""
            length = len(data)

            async with lock:
                writer.write(struct.pack("!I", length))
                writer.write(data)
                await writer.drain()

        except Exception:
            # On error, invalidate pool entry
            key = (target_host, target_port)
            if key in self.pool:
                with contextlib.suppress(BaseException):
                    self.pool[key][1].close()
                del self.pool[key]
            # Retry once? Or just fail.
            pass

    async def receive(self, timeout: float | None = None) -> Message:
        if timeout is not None:
            return await asyncio.wait_for(self.inbox.get(), timeout=timeout)
        return await self.inbox.get()
