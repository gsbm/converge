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

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": str}.
            **kwargs: Overrides (e.g. model, temperature).

        Returns:
            The assistant's reply content.
        """
        client = self._get_client()
        model = kwargs.pop("model", self.model)
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs,
        )
        choice = resp.choices[0] if resp.choices else None
        if choice is None:
            return ""
        return choice.message.content or ""
