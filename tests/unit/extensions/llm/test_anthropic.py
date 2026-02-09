"""Tests for converge.extensions.llm.anthropic."""

from unittest.mock import MagicMock, patch

import pytest

from converge.extensions.llm.anthropic import AnthropicProvider


def test_anthropic_provider_get_client_import_error():
    """Cover _get_client when anthropic is not installed (lines 25-34)."""
    import sys

    class FakeModule:
        def __getattr__(self, name):
            raise ImportError("No module named 'anthropic'")

    provider = AnthropicProvider(api_key="test")
    with patch.dict(sys.modules, {"anthropic": FakeModule()}), pytest.raises(
        ImportError, match="converge|Anthropic|anthropic",
    ):
        provider._get_client()


def test_anthropic_provider_chat():
    with patch.object(AnthropicProvider, "_get_client") as mock_get:
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="Hello")]
        mock_client.messages.create.return_value = mock_resp
        mock_get.return_value = mock_client

        provider = AnthropicProvider(api_key="test")
        result = provider.chat([{"role": "user", "content": "hi"}])
        assert result == "Hello"


def test_anthropic_provider_system_messages():
    with patch.object(AnthropicProvider, "_get_client") as mock_get:
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="OK")]
        mock_client.messages.create.return_value = mock_resp
        mock_get.return_value = mock_client

        provider = AnthropicProvider(api_key="test")
        result = provider.chat([
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "hi"},
        ])
        assert result == "OK"
        call_kw = mock_client.messages.create.call_args[1]
        assert call_kw.get("system") == "You are helpful"
        assert len(call_kw["messages"]) == 1


def test_anthropic_provider_chat_empty_content():
    with patch.object(AnthropicProvider, "_get_client") as mock_get:
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = []
        mock_client.messages.create.return_value = mock_resp
        mock_get.return_value = mock_client

        provider = AnthropicProvider(api_key="test")
        result = provider.chat([{"role": "user", "content": "hi"}])
        assert result == ""


def test_anthropic_provider_chat_content_block_no_text():
    with patch.object(AnthropicProvider, "_get_client") as mock_get:
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = [object()]
        mock_client.messages.create.return_value = mock_resp
        mock_get.return_value = mock_client

        provider = AnthropicProvider(api_key="test")
        result = provider.chat([{"role": "user", "content": "hi"}])
        assert result == ""
