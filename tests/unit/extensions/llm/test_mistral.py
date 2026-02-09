"""Tests for converge.extensions.llm.mistral."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from converge.extensions.llm.mistral import MistralProvider


def test_mistral_provider_get_client_import_error():
    """Cover _get_client when mistralai is not installed (lines 25-34)."""

    class FakeModule:
        def __getattr__(self, name):
            raise ImportError("No module named 'mistralai'")

    provider = MistralProvider(api_key="test")
    with patch.dict(sys.modules, {"mistralai": FakeModule()}), pytest.raises(
        ImportError, match="converge|Mistral|mistralai",
    ):
        provider._get_client()


def test_mistral_provider_chat():
    with patch.object(MistralProvider, "_get_client") as mock_get:
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="Hi"))]
        mock_client.chat.complete.return_value = mock_resp
        mock_get.return_value = mock_client

        provider = MistralProvider(api_key="test")
        result = provider.chat([{"role": "user", "content": "hi"}])
        assert result == "Hi"


def test_mistral_provider_empty_response():
    with patch.object(MistralProvider, "_get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.chat.complete.return_value = None
        mock_get.return_value = mock_client

        provider = MistralProvider(api_key="test")
        result = provider.chat([{"role": "user", "content": "hi"}])
        assert result == ""


def test_mistral_provider_chat_no_choices():
    with patch.object(MistralProvider, "_get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.chat.complete.return_value = MagicMock(choices=[])
        mock_get.return_value = mock_client

        provider = MistralProvider(api_key="test")
        result = provider.chat([{"role": "user", "content": "hi"}])
        assert result == ""
