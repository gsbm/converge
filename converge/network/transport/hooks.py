from __future__ import annotations

import logging
from typing import Any, Protocol

from converge.core.message import Message

from .base import Transport

logger = logging.getLogger(__name__)


class MessageHook(Protocol):
    def pre_send(self, message: Message) -> Message | None:
        ...

    def post_receive(self, message: Message) -> Message | None:
        ...

    def on_error(self, stage: str, error: Exception, context: dict[str, Any]) -> None:
        ...


class HookedTransport(Transport):
    """
    Transport wrapper that applies message hooks around send/receive.
    """

    def __init__(self, base_transport: Transport, hooks: list[MessageHook] | None = None):
        self.base_transport = base_transport
        self.hooks = hooks or []

    async def start(self) -> None:
        await self.base_transport.start()

    async def stop(self) -> None:
        await self.base_transport.stop()

    async def send(self, message: Message) -> None:
        current: Message | None = message
        for hook in self.hooks:
            if current is None:
                return
            try:
                current = hook.pre_send(current)
            except Exception as e:
                self._on_error(hook, "pre_send", e, {"message_id": getattr(current, "id", "")})
                raise
        if current is None:
            return
        await self.base_transport.send(current)

    async def receive(self, timeout: float | None = None) -> Message:
        message = await self.base_transport.receive(timeout=timeout)
        current: Message | None = message
        for hook in self.hooks:
            if current is None:
                break
            try:
                current = hook.post_receive(current)
            except Exception as e:
                self._on_error(hook, "post_receive", e, {"message_id": getattr(current, "id", "")})
                raise
        if current is None:
            raise TimeoutError("message dropped by post_receive hook")
        return current

    async def receive_verified(self, identity_registry, timeout: float | None = None) -> Message | None:
        message = await self.base_transport.receive_verified(identity_registry, timeout=timeout)
        if message is None:
            return None
        current: Message | None = message
        for hook in self.hooks:
            if current is None:
                return None
            try:
                current = hook.post_receive(current)
            except Exception as e:
                self._on_error(hook, "post_receive", e, {"message_id": getattr(current, "id", "")})
                raise
        return current

    def _on_error(self, hook: MessageHook, stage: str, error: Exception, context: dict[str, Any]) -> None:
        callback = getattr(hook, "on_error", None)
        if not callable(callback):
            return
        try:
            callback(stage, error, context)
        except Exception:
            logger.debug("Hook error callback failed", exc_info=True)
