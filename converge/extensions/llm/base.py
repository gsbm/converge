"""LLM provider protocol."""

from typing import Any, Protocol


class LLMProvider(Protocol):
    """
    Protocol for LLM providers.
    Implementations produce text completions from a list of messages.
    """

    def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        """
        Send messages to the LLM and return the completion text.

        Args:
            messages: List of message dicts with "role" and "content" keys.
            **kwargs: Provider-specific options (model, temperature, etc.).

        Returns:
            The model's response text.
        """
        ...
