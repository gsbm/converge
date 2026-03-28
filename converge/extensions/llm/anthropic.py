"""Anthropic provider for the LLM extension."""

import json
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
        When use_structured_output=True and emit_decisions_tool is provided, uses tools API
        and returns the tool use input (JSON string).

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": str}.
            **kwargs: Overrides. use_structured_output and emit_decisions_tool enable structured output.

        Returns:
            The assistant's reply content, or the emit_decisions tool input when structured.
        """
        use_structured = kwargs.pop("use_structured_output", False)
        emit_tool = kwargs.pop("emit_decisions_tool", None)
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
        create_kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": anthropic_messages,
            **kwargs,
        }
        if system:
            create_kwargs["system"] = system
        if use_structured and emit_tool:
            fn = emit_tool.get("function") or {}
            create_kwargs["tools"] = [{
                "name": fn.get("name", "emit_decisions"),
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
            }]
            create_kwargs["tool_choice"] = {"type": "tool", "name": "emit_decisions"}

        resp = client.messages.create(**create_kwargs)
        if not resp.content:
            return ""
        if use_structured and emit_tool:
            for block in resp.content:
                if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == "emit_decisions":
                    raw = getattr(block, "input", None)
                    if raw is not None:
                        return json.dumps(raw) if isinstance(raw, dict) else str(raw)
            return ""
        parts = []
        for block in resp.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "".join(parts)
