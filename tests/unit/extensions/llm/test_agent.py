"""Tests for converge.extensions.llm.agent."""

import json
from unittest.mock import MagicMock

import pytest

from converge.core.identity import Identity
from converge.extensions.llm import LLMAgent


class MockProvider:
    """Mock LLM provider for testing."""

    def __init__(self, responses: list[str]):
        self.responses = responses
        self.call_count = 0

    def chat(self, messages: list, **kwargs) -> str:
        idx = min(self.call_count, len(self.responses) - 1)
        self.call_count += 1
        return self.responses[idx]


def test_llm_agent_decide_parses_send_message():
    identity = Identity.generate()
    provider = MockProvider([
        '[{"type": "SendMessage", "message": {"sender": "' + identity.fingerprint
        + '", "topics": [], "payload": {"greeting": "hi"}}}]',
    ])
    agent = LLMAgent(identity, provider=provider)

    decisions = agent.decide([], [])

    assert len(decisions) == 1
    from converge.core.decisions import SendMessage

    assert isinstance(decisions[0], SendMessage)
    assert decisions[0].message.payload == {"greeting": "hi"}


def test_llm_agent_decide_empty_array():
    identity = Identity.generate()
    provider = MockProvider(["[]"])
    agent = LLMAgent(identity, provider=provider)

    decisions = agent.decide([], [])

    assert decisions == []


def test_llm_agent_decide_invalid_json_returns_empty():
    identity = Identity.generate()
    provider = MockProvider(["not valid json"])
    agent = LLMAgent(identity, provider=provider)

    decisions = agent.decide([], [])

    assert decisions == []


def test_llm_agent_decide_provider_error_returns_empty():
    identity = Identity.generate()
    provider = MagicMock()
    provider.chat.side_effect = Exception("API error")
    agent = LLMAgent(identity, provider=provider)

    decisions = agent.decide([], [])

    assert decisions == []


def test_llm_agent_formats_messages():
    identity = Identity.generate()
    from converge.core.message import Message

    msg = Message(sender="other", payload={"x": 1})
    provider = MagicMock()
    provider.chat.return_value = "[]"
    agent = LLMAgent(identity, provider=provider)

    agent.decide([msg], [])

    assert provider.chat.called
    messages = provider.chat.call_args[0][0]
    assert len(messages) >= 2
    assert any("Messages:" in (m.get("content") or "") for m in messages)


def test_llm_agent_parse_join_leave_claim_submit():
    identity = Identity.generate()
    provider = MagicMock()
    provider.chat.return_value = json.dumps([
        {"type": "JoinPool", "pool_id": "p1"},
        {"type": "LeavePool", "pool_id": "p2"},
        {"type": "ClaimTask", "task_id": "t1"},
        {"type": "SubmitTask", "task": {"id": "t2", "objective": {"goal": "x"}, "inputs": {}}},
    ])
    agent = LLMAgent(identity, provider=provider)
    decisions = agent.decide([], [])
    assert len(decisions) == 4
    from converge.core.decisions import ClaimTask, JoinPool, LeavePool, SubmitTask

    assert isinstance(decisions[0], JoinPool)
    assert decisions[0].pool_id == "p1"
    assert isinstance(decisions[1], LeavePool)
    assert isinstance(decisions[2], ClaimTask)
    assert decisions[2].task_id == "t1"
    assert isinstance(decisions[3], SubmitTask)
    assert decisions[3].task.id == "t2"


def test_llm_agent_format_empty_messages_tasks():
    identity = Identity.generate()
    provider = MagicMock()
    provider.chat.return_value = "[]"
    agent = LLMAgent(identity, provider=provider)
    agent.decide([], [])
    msgs = provider.chat.call_args[0][0]
    assert any("No messages or tasks" in (m.get("content") or "") for m in msgs)


def test_llm_agent_custom_system_prompt():
    identity = Identity.generate()
    provider = MagicMock()
    provider.chat.return_value = "[]"
    agent = LLMAgent(identity, provider=provider, system_prompt="Custom prompt")
    agent.decide([], [])
    call_args = provider.chat.call_args[0][0]
    assert any("Custom prompt" in (m.get("content") or "") for m in call_args)


def test_llm_agent_format_tasks_only():
    identity = Identity.generate()
    provider = MagicMock()
    provider.chat.return_value = "[]"
    from converge.core.task import Task

    agent = LLMAgent(identity, provider=provider)
    tasks = [Task(id="t1", objective={"goal": "x"})]
    agent.decide([], tasks)
    call_args = provider.chat.call_args[0][0]
    assert any("Tasks:" in (m.get("content") or "") for m in call_args)


def test_llm_agent_parse_send_message_invalid_returns_empty():
    identity = Identity.generate()
    provider = MagicMock()
    provider.chat.return_value = json.dumps([
        {"type": "SendMessage", "message": "not a dict"},
    ])
    agent = LLMAgent(identity, provider=provider)
    decisions = agent.decide([], [])
    assert len(decisions) == 0


def test_llm_agent_parse_submit_task_invalid_returns_empty():
    identity = Identity.generate()
    provider = MagicMock()
    provider.chat.return_value = json.dumps([
        {"type": "SubmitTask", "task": None},
    ])
    agent = LLMAgent(identity, provider=provider)
    decisions = agent.decide([], [])
    assert len(decisions) == 0


def test_llm_agent_parse_unknown_type_skipped():
    identity = Identity.generate()
    provider = MagicMock()
    provider.chat.return_value = json.dumps([
        {"type": "UnknownType", "x": 1},
    ])
    agent = LLMAgent(identity, provider=provider)
    decisions = agent.decide([], [])
    assert len(decisions) == 0


def test_llm_agent_parse_non_list_returns_empty():
    identity = Identity.generate()
    provider = MagicMock()
    provider.chat.return_value = json.dumps({"type": "SendMessage"})
    agent = LLMAgent(identity, provider=provider)
    decisions = agent.decide([], [])
    assert len(decisions) == 0


def test_llm_agent_parse_join_leave_claim_non_string_skipped():
    identity = Identity.generate()
    provider = MagicMock()
    provider.chat.return_value = json.dumps([
        {"type": "JoinPool", "pool_id": 123},
        {"type": "LeavePool", "pool_id": None},
        {"type": "ClaimTask", "task_id": 456},
    ])
    agent = LLMAgent(identity, provider=provider)
    decisions = agent.decide([], [])
    assert len(decisions) == 0


def test_llm_agent_format_messages_with_topics():
    from converge.core.message import Message
    from converge.core.topic import Topic

    identity = Identity.generate()
    msg = Message(sender="other", payload={"x": 1}, topics=[Topic("ns", {"k": "v"})])
    provider = MagicMock()
    provider.chat.return_value = "[]"
    agent = LLMAgent(identity, provider=provider)
    agent.decide([msg], [])
    call_args = provider.chat.call_args[0][0]
    content = call_args[1]["content"]
    assert "ns" in content and "k" in content


def test_openai_provider_import_error_without_openai():
    """OpenAIProvider raises helpful ImportError when openai not installed."""
    try:
        import openai  # noqa: F401
        pytest.skip("openai is installed")
    except ImportError:
        pass

    from converge.extensions.llm import OpenAIProvider

    provider = OpenAIProvider(api_key="test")
    with pytest.raises(ImportError, match="converge\\[llm\\]"):
        provider.chat([{"role": "user", "content": "hi"}])
