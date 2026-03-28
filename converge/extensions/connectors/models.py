from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class InboundWebhookEvent:
    provider: str
    source: str
    event_id: str
    occurred_at: float
    subject: str
    payload: dict[str, Any]
    headers: dict[str, str]
    trace_id: str | None = None


@dataclass(frozen=True)
class OutboundWebhookAction:
    target: str
    method: str
    url: str
    body: dict[str, Any]
    headers: dict[str, str] = field(default_factory=dict)
    idempotency_key: str | None = None
    deadline: float | None = None
