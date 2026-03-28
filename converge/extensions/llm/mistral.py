"""Mistral AI provider for the LLM extension."""

import os
from typing import Any


class MistralProvider:
    """
    LLM provider using the Mistral AI API.
    Requires mistralai>=1.0: pip install "converge[llm-mistral]"
    """

    def __init__(self, api_key: str | None = None, model: str = "mistral-small-latest"):
        """
        Initialize the Mistral provider.

        Args:
            api_key: Mistral API key. If None, uses MISTRAL_API_KEY env var.
            model: Model name (e.g. mistral-small-latest, mistral-large-latest).
        """
        self.api_key = api_key
        self.model = model
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from mistralai import Mistral
            except ImportError as e:
                raise ImportError(
                    "Mistral provider requires mistralai>=1.0. "
                    "Install with: pip install 'converge[llm-mistral]'",
                ) from e
            # SDK only reads MISTRAL_API_KEY when api_key is omitted (security=None).
            # Passing api_key=None builds Security(api_key=None) and no Authorization
            # header is sent, causing 401. So resolve from env when None.
            api_key = self.api_key or os.environ.get("MISTRAL_API_KEY") or None
            self._client = Mistral(api_key=api_key)
        return self._client

    def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        """
        Send messages to Mistral and return the completion text.
        When use_structured_output=True and emit_decisions_tool is provided, uses tool calling
        and returns the tool call arguments (JSON string).

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": str}.
            **kwargs: Overrides. use_structured_output and emit_decisions_tool enable structured output.

        Returns:
            The assistant's reply content, or the emit_decisions tool arguments when structured.
        """
        use_structured = kwargs.pop("use_structured_output", False)
        emit_tool = kwargs.pop("emit_decisions_tool", None)
        client = self._get_client()
        model = kwargs.pop("model", self.model)
        api_params: dict[str, Any] = {"model": model, "messages": messages, "stream": False, **kwargs}
        if use_structured and emit_tool:
            fn = emit_tool.get("function") or {}
            try:
                from mistralai.models import Function, Tool
                api_params["tools"] = [Tool(function=Function(
                    name=fn.get("name", "emit_decisions"),
                    description=fn.get("description", ""),
                    parameters=fn.get("parameters", {"type": "object", "properties": {}}),
                ))]
                api_params["tool_choice"] = "required"
            except ImportError:
                pass
        resp = client.chat.complete(**api_params)
        if not resp or not resp.choices:
            return ""
        choice = resp.choices[0]
        msg = getattr(choice, "message", None)
        if msg is None:
            return ""
        if use_structured and emit_tool and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls or []:
                f = getattr(tc, "function", None)
                if f and getattr(f, "name", None) == "emit_decisions":
                    args = getattr(f, "arguments", None) or ""
                    if args and isinstance(args, str):
                        return args.strip()
        content = getattr(msg, "content", None)
        return content or ""
