"""LLM-driven agent that uses an LLM provider for decide()."""

import asyncio
import contextlib
import inspect
import json
import logging
import re
from typing import Any

from converge.core.agent import Agent
from converge.core.decisions import (
    ClaimTask,
    CreatePool,
    InvokeTool,
    JoinPool,
    LeavePool,
    ReportTask,
    SendMessage,
    SubmitTask,
)
from converge.core.message import Message
from converge.core.task import Task

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an agent in a multi-agent system. Given incoming messages and tasks, output a JSON array of decisions.

Supported decision types:
- SendMessage: {"type": "SendMessage", "message": {"sender": "<agent_id>", "topics": [], "payload": {...}}}
- JoinPool: {"type": "JoinPool", "pool_id": "<pool_id>"}
- LeavePool: {"type": "LeavePool", "pool_id": "<pool_id>"}
- ClaimTask: {"type": "ClaimTask", "task_id": "<task_id>"}
- SubmitTask: {"type": "SubmitTask", "task": {"id": "<id>", "objective": {...}, "inputs": {...}}}
- ReportTask: {"type": "ReportTask", "task_id": "<task_id>", "result": {...}}
- CreatePool: {"type": "CreatePool", "spec": {"id": "<pool_id>", "topics": [...], "admission_policy": ...}}
- InvokeTool: {"type": "InvokeTool", "tool_name": "<name>", "params": {...}}

The message object must have: sender (str), topics (list of {"namespace": str, "attributes": dict}), payload (dict).
A task object must have: id, objective (dict), inputs (dict).
Output ONLY a valid JSON array. If you have no decisions, output [].
"""

# Tool definition for provider-native function calling (emit_decisions). Schema for the decision array.
EMIT_DECISIONS_TOOL = {
    "type": "function",
    "function": {
        "name": "emit_decisions",
        "description": "Emit a JSON array of decisions (SendMessage, JoinPool, ClaimTask, ReportTask, etc.).",
        "parameters": {
            "type": "object",
            "properties": {
                "decisions": {
                    "type": "array",
                    "description": "Array of decision objects, each with 'type' and type-specific fields.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "message": {"type": "object"},
                            "pool_id": {"type": "string"},
                            "task_id": {"type": "string"},
                            "result": {},
                            "task": {"type": "object"},
                            "spec": {"type": "object"},
                            "tool_name": {"type": "string"},
                            "params": {"type": "object"},
                        },
                    },
                },
            },
            "required": ["decisions"],
        },
    },
}


def _extract_json_array(response: str) -> str:
    """
    Extract a JSON array string from LLM response, handling markdown code blocks and stray text.
    - Strips leading/trailing whitespace.
    - Extracts content from ```json ... ``` or ``` ... ``` blocks.
    - Falls back to first [...] or {...} balanced span.
    """
    text = response.strip()
    if not text:
        return "[]"
    # Try markdown code blocks: ```json ... ``` or ``` ... ```
    code_block = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)
    match = code_block.search(text)
    if match:
        return match.group(1).strip()
    # Fallback: find first '[' or '{' and return balanced span
    for start_char, end_char in (("[", "]"), ("{", "}")):
        start = text.find(start_char)
        if start == -1:
            continue
        depth = 0
        in_string = None
        escape = False
        i = start
        while i < len(text):
            c = text[i]
            if escape:
                escape = False
                i += 1
                continue
            if c == "\\" and in_string:
                escape = True
                i += 1
                continue
            if in_string:
                if c == in_string:
                    in_string = None
                i += 1
                continue
            if c in ('"', "'"):
                in_string = c
                i += 1
                continue
            if c == start_char:
                depth += 1
            elif c == end_char:
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
            i += 1
    return text


class LLMAgent(Agent):
    """
    Agent that uses an LLM to produce decisions in decide().
    """

    def __init__(
        self,
        identity: Any,
        provider: Any,
        system_prompt: str | None = None,
        tool_registry: Any = None,
        *,
        use_structured_output: bool = False,
        on_decide_error: Any = None,
        memory: Any = None,
        few_shot_examples: list[tuple[str, str]] | None = None,
    ):
        """
        Initialize the LLM agent.

        Args:
            identity: Cryptographic identity (converge.core.identity.Identity).
            provider: LLM provider implementing ``chat(messages, **kwargs) -> str``.
            system_prompt: Optional override for the system prompt.
            tool_registry: Optional ToolRegistry; when set, tool schemas are injected into the system prompt (fallback path).
            use_structured_output: When True, request provider-native structured output (e.g. OpenAI function calling) when supported.
            on_decide_error: Optional callable (exception_or_message: Exception | str) -> None for observability when decide fails.
            memory: Optional ShortTermMemory (or object with append(role, content), get_messages()) for conversation history.
            few_shot_examples: Optional list of (user_content, assistant_json) example pairs to inject into the prompt.
        """
        super().__init__(identity)
        self.provider = provider
        self._system_prompt = system_prompt or _SYSTEM_PROMPT
        self._tool_registry = tool_registry
        self._use_structured_output = use_structured_output
        self._on_decide_error = on_decide_error
        self._memory = memory
        self._few_shot_examples = few_shot_examples or []

    def _get_system_prompt(self) -> str:
        """Return system prompt, appending tool schemas when tool_registry is set."""
        base = self._system_prompt
        if self._tool_registry is None:
            return base
        try:
            tools = self._tool_registry.to_provider_tools()
        except Exception:
            return base
        if not tools:
            return base
        lines = [base, "", "Available tools (use InvokeTool with tool_name and params):"]
        for t in tools:
            fn = t.get("function") or {}
            name = fn.get("name", "")
            desc = fn.get("description", "")
            params = fn.get("parameters", {})
            lines.append(f"- {name}: {desc}")
            lines.append(f"  params schema: {json.dumps(params)}")
        return "\n".join(lines)

    def _format_messages_and_tasks(self, messages: list[Any], tasks: list[Any], tool_observations: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
        """Format messages, tasks, and optional tool observations for the LLM."""
        parts = []
        if messages:
            msgs_data = []
            for m in messages:
                msg_dict = {"sender": getattr(m, "sender", ""), "payload": getattr(m, "payload", {})}
                if hasattr(m, "topics") and m.topics:
                    msg_dict["topics"] = [
                        {"namespace": t.namespace, "attributes": getattr(t, "attributes", {})}
                        for t in m.topics
                    ]
                else:
                    msg_dict["topics"] = []
                msgs_data.append(msg_dict)
            parts.append(f"Messages: {json.dumps(msgs_data)}")
        if tasks:
            tasks_data = [
                {"id": getattr(t, "id", ""), "objective": getattr(t, "objective", {})}
                for t in tasks
            ]
            parts.append(f"Tasks: {json.dumps(tasks_data)}")
        if tool_observations:
            parts.append("Tool observations (previous tool results): " + json.dumps(tool_observations))
        if not parts:
            out = [{"role": "system", "content": self._get_system_prompt()}, {"role": "user", "content": "No messages or tasks. Output []."}]
            if self._memory is not None and hasattr(self._memory, "get_messages"):
                out = [out[0], *self._memory.get_messages(), out[1]]
            return out
        content = "\n".join(parts)
        user_content: str | dict[str, str] = content
        out: list[dict[str, Any]] = [{"role": "system", "content": self._get_system_prompt()}]
        if self._memory is not None and hasattr(self._memory, "get_messages"):
            out.extend(self._memory.get_messages())
        for u, a in (self._few_shot_examples or [])[:2]:
            out.append({"role": "user", "content": u})
            out.append({"role": "assistant", "content": a})
        out.append({"role": "user", "content": user_content})
        return out

    def _parse_decisions(self, response: str) -> tuple[list[Any], bool]:
        """Parse LLM response JSON into decision objects. Returns (decisions, parsed_ok)."""
        extracted = _extract_json_array(response)
        try:
            data = json.loads(extracted)
        except json.JSONDecodeError:
            logger.warning("LLM response is not valid JSON: %s", response[:200], exc_info=True)
            return [], False
        if isinstance(data, dict) and "decisions" in data:
            data = data["decisions"]
        if not isinstance(data, list):
            return [], False
        decisions = []
        for item in data:
            if not isinstance(item, dict):
                continue
            dtype = item.get("type")
            if dtype == "SendMessage":
                raw = item.get("message")
                if isinstance(raw, dict):
                    try:
                        msg_data = {
                            "id": raw.get("id", ""),
                            "sender": raw.get("sender") or self.id,
                            "topics": raw.get("topics", []),
                            "payload": raw.get("payload", {}),
                            "task_id": raw.get("task_id"),
                            "timestamp": raw.get("timestamp", 0),
                            "signature": raw.get("signature", b""),
                        }
                        msg = Message.from_dict(msg_data)
                        decisions.append(SendMessage(msg))
                    except Exception as e:
                        logger.warning("Failed to parse SendMessage: %s", e)
            elif dtype == "JoinPool":
                pool_id = item.get("pool_id")
                if isinstance(pool_id, str):
                    decisions.append(JoinPool(pool_id))
            elif dtype == "LeavePool":
                pool_id = item.get("pool_id")
                if isinstance(pool_id, str):
                    decisions.append(LeavePool(pool_id))
            elif dtype == "ClaimTask":
                task_id = item.get("task_id")
                if isinstance(task_id, str):
                    decisions.append(ClaimTask(task_id))
            elif dtype == "SubmitTask":
                raw = item.get("task")
                if isinstance(raw, dict):
                    try:
                        task = Task(
                            id=raw.get("id", ""),
                            objective=raw.get("objective", {}),
                            inputs=raw.get("inputs", {}),
                        )
                        decisions.append(SubmitTask(task))
                    except Exception as e:
                        logger.warning("Failed to parse SubmitTask: %s", e)
            elif dtype == "ReportTask":
                task_id = item.get("task_id")
                if isinstance(task_id, str):
                    result = item.get("result")
                    decisions.append(ReportTask(task_id=task_id, result=result))
            elif dtype == "CreatePool":
                spec = item.get("spec")
                if isinstance(spec, dict):
                    decisions.append(CreatePool(spec=spec))
            elif dtype == "InvokeTool":
                tool_name = item.get("tool_name")
                params = item.get("params")
                if isinstance(tool_name, str):
                    params = params if isinstance(params, dict) else {}
                    decisions.append(InvokeTool(tool_name=tool_name, params=params))
        return decisions, True

    async def _call_provider_with_retry(self, chat_messages: list[dict[str, Any]], **extra: Any) -> str:
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                if self._use_structured_output:
                    extra = {
                        **extra,
                        "use_structured_output": True,
                        "emit_decisions_tool": EMIT_DECISIONS_TOOL,
                    }
                achat = getattr(self.provider, "achat", None)
                if inspect.iscoroutinefunction(achat):
                    return await achat(chat_messages, **extra)
                return await asyncio.to_thread(self.provider.chat, chat_messages, **extra)
            except Exception as e:
                if isinstance(e, asyncio.CancelledError):
                    raise
                last_err = e
                err_str = str(e).lower()
                if attempt < 2 and ("rate" in err_str or "timeout" in err_str or "429" in err_str or "503" in err_str):
                    await asyncio.sleep(2**attempt)
                    continue
                raise
        raise last_err or RuntimeError("no response")

    async def adecide(
        self,
        messages: list[Any],
        tasks: list[Any],
        tool_observations: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> list[Any]:
        """
        Use the LLM to produce decisions from messages and tasks.

        Args:
            messages: Incoming messages from the inbox.
            tasks: Task updates or assignments.
            tool_observations: Optional list of {tool_name, params, result} from previous InvokeTool (ReAct loop).
            **kwargs: Ignored; for compatibility with base decide().

        Returns:
            List of Decision objects (e.g. SendMessage).
        """
        repair_prompt = "Your previous response was not valid JSON. Output ONLY a valid JSON array of decisions, no other text."
        chat_messages = self._format_messages_and_tasks(messages, tasks, tool_observations=tool_observations)

        try:
            response = await self._call_provider_with_retry(chat_messages)
        except Exception as e:
            logger.warning("LLM provider error: %s", e)
            if self._on_decide_error is not None:
                with contextlib.suppress(Exception):
                    self._on_decide_error(e)
            return []
        decisions, parsed_ok = self._parse_decisions(response)
        if not parsed_ok and response.strip():
            chat_messages.append({"role": "user", "content": repair_prompt})
            try:
                response = await self._call_provider_with_retry(chat_messages)
            except Exception as e:
                logger.warning("LLM provider error on repair: %s", e)
                if self._on_decide_error is not None:
                    with contextlib.suppress(Exception):
                        self._on_decide_error(e)
                return []
            decisions, _ = self._parse_decisions(response)
        if self._memory is not None and hasattr(self._memory, "append") and chat_messages:
            last_user = next((m.get("content") for m in reversed(chat_messages) if m.get("role") == "user"), None)
            if last_user is not None:
                self._memory.append("user", last_user)
                self._memory.append("assistant", response)
        return decisions

    def decide(self, messages: list[Any], tasks: list[Any], tool_observations: list[dict[str, Any]] | None = None, **kwargs: Any) -> list[Any]:
        """
        Synchronous wrapper for compatibility outside async runtimes.

        In async runtimes, use ``await adecide(...)``.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.adecide(messages, tasks, tool_observations=tool_observations, **kwargs),
            )
        raise RuntimeError("LLMAgent.decide() called inside an active event loop; use await adecide().")
