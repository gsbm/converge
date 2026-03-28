"""Optional short-term memory for agent conversation history."""

from typing import Any


class ShortTermMemory:
    """
    Bounded conversation history (e.g. last N messages or turns).
    Used by LLMAgent to retain context across decide() calls.
    """

    def __init__(self, max_messages: int = 20):
        """
        Args:
            max_messages: Maximum number of messages to retain; oldest are dropped when exceeded.
        """
        self.max_messages = max(1, max_messages)
        self._messages: list[dict[str, Any]] = []

    def append(self, role: str, content: str | dict[str, Any]) -> None:
        """Append one message. Trims if over max_messages."""
        self._messages.append({"role": role, "content": content})
        while len(self._messages) > self.max_messages:
            self._messages.pop(0)

    def get_messages(self) -> list[dict[str, Any]]:
        """Return a copy of the current message list."""
        return list(self._messages)

    def clear(self) -> None:
        """Clear all messages."""
        self._messages.clear()
