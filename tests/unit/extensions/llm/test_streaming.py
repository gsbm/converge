"""Tests for optional LLM streaming (chat_stream)."""


import pytest


class _MockStreamingProvider:
    """Mock provider that implements chat_stream."""

    def chat(self, messages, **kwargs):
        return "full response"

    async def chat_stream(self, messages, **kwargs):
        for token in ["Hello", " ", "world"]:
            yield token


@pytest.mark.asyncio
async def test_chat_stream_optional():
    """Providers can optionally implement chat_stream; we can consume it."""
    provider = _MockStreamingProvider()
    tokens = []
    async for t in provider.chat_stream([{"role": "user", "content": "hi"}]):
        tokens.append(t)
    assert tokens == ["Hello", " ", "world"]
    assert provider.chat([]) == "full response"
