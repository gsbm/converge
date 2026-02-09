"""Anthropic provider for the LLM extension."""

from typing import Any


class AnthropicProvider:
    """
    LLM provider using the Anthropic API.
    Requires anthropic>=0.18: pip install "converge[llm-anthropic]"
    """

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize the Anthropic provider.

        Args:
            api_key: Anthropic API key. If None, uses ANTHROPIC_API_KEY env var.
            model: Model name (e.g. claude-sonnet-4-20250514, claude-3-5-haiku).
        """
        self.api_key = api_key
        self.model = model
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from anthropic import Anthropic
            except ImportError as e:
                raise ImportError(
                    "Anthropic provider requires anthropic>=0.18. "
                    "Install with: pip install 'converge[llm-anthropic]'",
                ) from e
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        """
        Send messages to Anthropic and return the completion text.

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": str}.
            **kwargs: Overrides (e.g. model, max_tokens).

        Returns:
            The assistant's reply content.
        """
        client = self._get_client()
        model = kwargs.pop("model", self.model)
        max_tokens = kwargs.pop("max_tokens", 1024)

        system_parts: list[str] = []
        anthropic_messages: list[dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_parts.append(content if isinstance(content, str) else str(content))
            else:
                anthropic_messages.append({"role": role, "content": content})

        system = "\n".join(system_parts) if system_parts else None
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=anthropic_messages,
            system=system,
            **kwargs,
        )
        if not resp.content:
            return ""
        parts = []
        for block in resp.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "".join(parts)
