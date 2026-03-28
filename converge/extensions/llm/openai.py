"""OpenAI provider for the LLM extension."""

from typing import Any


class OpenAIProvider:
    """
    LLM provider using the OpenAI API.
    Requires openai>=1.0: pip install "converge[llm]"
    """

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        """
        Initialize the OpenAI provider.

        Args:
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.
            model: Model name (e.g. gpt-4o-mini, gpt-4o).
        """
        self.api_key = api_key
        self.model = model
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as e:
                raise ImportError(
                    "OpenAI provider requires openai>=1.0. Install with: pip install 'converge[llm]'",
                ) from e
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        """
        Send messages to OpenAI and return the completion text.
        When use_structured_output=True and emit_decisions_tool is provided, uses function calling
        and returns the tool call arguments (JSON string of decision array).

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": str}.
            **kwargs: Overrides (e.g. model, temperature). use_structured_output=True and
                emit_decisions_tool=<dict> enable structured decision output via tool call.

        Returns:
            The assistant's reply content, or the emit_decisions tool call arguments when structured.
        """
        use_structured = kwargs.pop("use_structured_output", False)
        emit_tool = kwargs.pop("emit_decisions_tool", None)
        client = self._get_client()
        model = kwargs.pop("model", self.model)
        api_params = {"model": model, "messages": messages, **kwargs}
        if use_structured and emit_tool:
            api_params["tools"] = [emit_tool]
            api_params["tool_choice"] = {"type": "function", "function": {"name": "emit_decisions"}}
        resp = client.chat.completions.create(**api_params)
        choice = resp.choices[0] if resp.choices else None
        if choice is None:
            return ""
        msg = choice.message
        if use_structured and emit_tool and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls or []:
                if getattr(tc, "function", None) and getattr(tc.function, "name", None) == "emit_decisions":
                    args = getattr(tc.function, "arguments", None) or ""
                    if args.strip():
                        return args.strip()
        return msg.content or ""
