"""Tests for converge.extensions.llm.agent."""

import json
from unittest.mock import MagicMock

import pytest

from converge.core.identity import Identity
from converge.extensions.llm import LLMAgent
from converge.extensions.llm.agent import _extract_json_array


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


def test_llm_agent_parse_report_task_create_pool_invoke_tool():
    """Parse valid ReportTask, CreatePool, InvokeTool decisions."""
    identity = Identity.generate()
    provider = MagicMock()
    provider.chat.return_value = json.dumps([
        {"type": "ReportTask", "task_id": "t1", "result": {"status": "done", "output": 42}},
        {"type": "CreatePool", "spec": {"id": "new-pool", "topics": []}},
        {"type": "InvokeTool", "tool_name": "search", "params": {"query": "x"}},
    ])
    agent = LLMAgent(identity, provider=provider)
    decisions = agent.decide([], [])
    assert len(decisions) == 3
    from converge.core.decisions import CreatePool, InvokeTool, ReportTask

    assert isinstance(decisions[0], ReportTask)
    assert decisions[0].task_id == "t1"
    assert decisions[0].result == {"status": "done", "output": 42}
    assert isinstance(decisions[1], CreatePool)
    assert decisions[1].spec == {"id": "new-pool", "topics": []}
    assert isinstance(decisions[2], InvokeTool)
    assert decisions[2].tool_name == "search"
    assert decisions[2].params == {"query": "x"}


def test_llm_agent_parse_report_task_invalid_task_id_skipped():
    """ReportTask with non-string task_id is skipped."""
    identity = Identity.generate()
    provider = MagicMock()
    provider.chat.return_value = json.dumps([
        {"type": "ReportTask", "task_id": 123, "result": {}},
        {"type": "ReportTask", "result": {}},
    ])
    agent = LLMAgent(identity, provider=provider)
    decisions = agent.decide([], [])
    assert len(decisions) == 0


def test_llm_agent_parse_create_pool_invalid_spec_skipped():
    """CreatePool with non-dict spec is skipped."""
    identity = Identity.generate()
    provider = MagicMock()
    provider.chat.return_value = json.dumps([
        {"type": "CreatePool", "spec": "not-a-dict"},
        {"type": "CreatePool", "spec": None},
    ])
    agent = LLMAgent(identity, provider=provider)
    decisions = agent.decide([], [])
    assert len(decisions) == 0


def test_llm_agent_parse_invoke_tool_invalid_skipped():
    """InvokeTool with non-string tool_name is skipped; missing params default to {}."""
    identity = Identity.generate()
    provider = MagicMock()
    provider.chat.return_value = json.dumps([
        {"type": "InvokeTool", "tool_name": 999, "params": {}},
        {"type": "InvokeTool", "tool_name": "ok", "params": {}},
    ])
    agent = LLMAgent(identity, provider=provider)
    decisions = agent.decide([], [])
    assert len(decisions) == 1
    from converge.core.decisions import InvokeTool

    assert isinstance(decisions[0], InvokeTool)
    assert decisions[0].tool_name == "ok"
    assert decisions[0].params == {}


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


# --- _extract_json_array ---


def test_extract_json_array_raw_array():
    """Raw JSON array is returned as-is (after strip)."""
    raw = '  [{"type": "ClaimTask", "task_id": "t1"}]  '
    out = _extract_json_array(raw)
    assert json.loads(out) == [{"type": "ClaimTask", "task_id": "t1"}]


def test_extract_json_array_markdown_json_block():
    """Content inside ```json ... ``` is extracted."""
    text = """Here is the result:
```json
[{"type": "JoinPool", "pool_id": "p1"}]
```
Done."""
    out = _extract_json_array(text)
    assert json.loads(out) == [{"type": "JoinPool", "pool_id": "p1"}]


def test_extract_json_array_markdown_generic_block():
    """Content inside ``` ... ``` (no json label) is extracted."""
    text = """Output:
```
[{"type": "ReportTask", "task_id": "t1", "result": {}}]
```"""
    out = _extract_json_array(text)
    assert json.loads(out) == [{"type": "ReportTask", "task_id": "t1", "result": {}}]


def test_extract_json_array_fallback_brackets():
    """Fallback finds first balanced [...] span."""
    text = 'Some preamble [{"type": "LeavePool", "pool_id": "p1"}] trailing'
    out = _extract_json_array(text)
    assert json.loads(out) == [{"type": "LeavePool", "pool_id": "p1"}]


def test_extract_json_array_empty_string():
    """Empty or whitespace returns []."""
    assert _extract_json_array("") == "[]"
    assert _extract_json_array("   ") == "[]"


def test_extract_json_array_invalid_no_brackets():
    """When no brackets, returns raw text (may not parse)."""
    text = "not valid json at all"
    out = _extract_json_array(text)
    assert out == text
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)


def test_llm_agent_tool_registry_injects_schema_into_prompt():
    """When tool_registry is set, system prompt includes tool info."""
    from converge.core.tools import ToolRegistry

    class ToolWithSchema:
        @property
        def name(self):
            return "my_tool"
        @property
        def schema(self):
            return {"properties": {"x": {"type": "string"}}}
        def run(self, params):
            return params

    registry = ToolRegistry()
    registry.register(ToolWithSchema())
    identity = Identity.generate()
    provider = MagicMock()
    provider.chat.return_value = "[]"
    agent = LLMAgent(identity, provider=provider, tool_registry=registry)
    prompt = agent._get_system_prompt()
    assert "Available tools" in prompt
    assert "my_tool" in prompt
    assert "x" in prompt


def test_llm_agent_parse_decisions_from_tool_call_format():
    """When response is tool-call format with decisions key, parse correctly."""
    identity = Identity.generate()
    provider = MagicMock()
    provider.chat.return_value = json.dumps({"decisions": [{"type": "ClaimTask", "task_id": "t1"}]})
    agent = LLMAgent(identity, provider=provider)
    decisions, ok = agent._parse_decisions(provider.chat.return_value)
    assert ok is True
    assert len(decisions) == 1
    from converge.core.decisions import ClaimTask
    assert isinstance(decisions[0], ClaimTask)
    assert decisions[0].task_id == "t1"


def test_llm_agent_on_decide_error_callback():
    """When provider raises, on_decide_error is called."""
    identity = Identity.generate()
    provider = MagicMock()
    provider.chat.side_effect = RuntimeError("API down")
    errors = []
    agent = LLMAgent(identity, provider=provider, on_decide_error=errors.append)
    decisions = agent.decide([], [])
    assert decisions == []
    assert len(errors) == 1
    assert "API down" in str(errors[0])


def test_llm_agent_memory_included_in_prompt():
    """When memory is set, its messages are included in the prompt sent to the provider."""
    from converge.core.memory import ShortTermMemory

    identity = Identity.generate()
    provider = MagicMock()
    provider.chat.return_value = "[]"
    memory = ShortTermMemory(max_messages=10)
    memory.append("user", "first")
    memory.append("assistant", "[]")
    agent = LLMAgent(identity, provider=provider, memory=memory)
    agent.decide([], [])
    call_args = provider.chat.call_args[0][0]
    assert len(call_args) >= 3
    assert call_args[1]["role"] == "user" and call_args[1]["content"] == "first"
    assert call_args[2]["role"] == "assistant"
