"""Tests for converge.extensions.llm.openai."""

from unittest.mock import MagicMock, patch

import pytest

from converge.extensions.llm import OpenAIProvider


def test_openai_provider_get_client_import_error():
    """Cover _get_client when openai is not installed (lines 25-29)."""
    import sys

    class FakeModule:
        def __getattr__(self, name):
            raise ImportError("No module named 'openai'")

    provider = OpenAIProvider(api_key="test")
    with patch.dict(sys.modules, {"openai": FakeModule()}), pytest.raises(
        ImportError, match="converge|OpenAI|openai",
    ):
        provider._get_client()


def test_openai_provider_chat():
    try:
        import openai  # noqa: F401
    except ImportError:
        pytest.skip("openai not installed")

    with patch("openai.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="Hi"))]
        mock_client.chat.completions.create.return_value = mock_resp
        mock_cls.return_value = mock_client

        provider = OpenAIProvider(api_key="test")
        result = provider.chat([{"role": "user", "content": "hi"}])
        assert result == "Hi"


def test_openai_provider_chat_empty_choices():
    try:
        import openai  # noqa: F401
    except ImportError:
        pytest.skip("openai not installed")

    with patch("openai.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(choices=[])
        mock_cls.return_value = mock_client

        provider = OpenAIProvider(api_key="test")
        result = provider.chat([{"role": "user", "content": "hi"}])
        assert result == ""
