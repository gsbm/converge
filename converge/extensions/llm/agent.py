"""LLM-driven agent that uses an LLM provider for decide()."""

import json
import logging
from typing import Any

from converge.core.agent import Agent
from converge.core.decisions import (
    ClaimTask,
    JoinPool,
    LeavePool,
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

The message object must have: sender (str), topics (list of {"namespace": str, "attributes": dict}), payload (dict).
A task object must have: id, objective (dict), inputs (dict).
Output ONLY a valid JSON array. If you have no decisions, output [].
"""


class LLMAgent(Agent):
    """
    Agent that uses an LLM to produce decisions in decide().
    """

    def __init__(self, identity: Any, provider: Any, system_prompt: str | None = None):
        """
        Initialize the LLM agent.

        Args:
            identity: Cryptographic identity (converge.core.identity.Identity).
            provider: LLM provider implementing ``chat(messages, **kwargs) -> str``.
            system_prompt: Optional override for the system prompt.
        """
        super().__init__(identity)
        self.provider = provider
        self._system_prompt = system_prompt or _SYSTEM_PROMPT

    def _format_messages_and_tasks(self, messages: list[Any], tasks: list[Any]) -> list[dict[str, str]]:
        """Format messages and tasks for the LLM."""
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
        if not parts:
            return [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": "No messages or tasks. Output []."},
            ]
        content = "\n".join(parts)
        return [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": content},
        ]

    def _parse_decisions(self, response: str) -> list[Any]:
        """Parse LLM response JSON into decision objects."""
        try:
            data = json.loads(response.strip())
        except json.JSONDecodeError:
            logger.warning("LLM response is not valid JSON: %s", response[:200])
            return []
        if not isinstance(data, list):
            return []
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
        return decisions

    def decide(self, messages: list[Any], tasks: list[Any]) -> list[Any]:
        """
        Use the LLM to produce decisions from messages and tasks.

        Args:
            messages: Incoming messages from the inbox.
            tasks: Task updates or assignments.

        Returns:
            List of Decision objects (e.g. SendMessage).
        """
        chat_messages = self._format_messages_and_tasks(messages, tasks)
        try:
            response = self.provider.chat(chat_messages)
        except Exception as e:
            logger.warning("LLM provider error: %s", e)
            return []
        return self._parse_decisions(response)
