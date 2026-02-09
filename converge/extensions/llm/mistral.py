"""Mistral AI provider for the LLM extension."""

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
            self._client = Mistral(api_key=self.api_key)
        return self._client

    def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        """
        Send messages to Mistral and return the completion text.

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": str}.
            **kwargs: Overrides (e.g. model, max_tokens, temperature).

        Returns:
            The assistant's reply content.
        """
        client = self._get_client()
        model = kwargs.pop("model", self.model)
        resp = client.chat.complete(
            model=model,
            messages=messages,
            stream=False,
            **kwargs,
        )
        if not resp or not resp.choices:
            return ""
        choice = resp.choices[0]
        msg = getattr(choice, "message", None)
        if msg is None:
            return ""
        content = getattr(msg, "content", None)
        return content or ""
