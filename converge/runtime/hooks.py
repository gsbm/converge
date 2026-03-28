from __future__ import annotations

from typing import Any, Protocol

from converge.core.message import Message


class RuntimeHook(Protocol):
    def on_fallback_pre_send(self, message: Message) -> Message | None:
        ...

    def on_unverified_drop(self, context: dict[str, Any]) -> None:
        ...
