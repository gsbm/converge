from __future__ import annotations

import asyncio
import inspect
import json
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict
from typing import Any

from converge.core.message import Message
from converge.core.store import Store
from converge.core.task import Task
from converge.core.topic import Topic
from converge.extensions.storage.memory import MemoryStore
from converge.observability.logging import get_logger, log_struct
from converge.observability.metrics import MetricsCollector

from .models import InboundWebhookEvent, OutboundWebhookAction
from .retry import CircuitBreaker, WebhookRetryPolicy
from .security import ProviderProfile, WebhookSecurity, WebhookSecurityError, WebhookSecurityPolicy

logger = get_logger(__name__)


class WebhookConnector:
    """
    Generic webhook bridge with strict inbound verification and reliable outbound dispatch.
    """

    def __init__(
        self,
        *,
        provider_profiles: dict[str, ProviderProfile],
        secrets: dict[str, str],
        security_policy: WebhookSecurityPolicy | None = None,
        retry_policy: WebhookRetryPolicy | None = None,
        store: Store | None = None,
        metrics_collector: MetricsCollector | None = None,
        connector_id: str = "webhook-connector",
        outbound_sender: Any | None = None,
    ) -> None:
        self.store = store or MemoryStore()
        self.metrics = metrics_collector or MetricsCollector()
        self.security_policy = security_policy or WebhookSecurityPolicy()
        self.retry_policy = retry_policy or WebhookRetryPolicy()
        self.security = WebhookSecurity(
            self.security_policy,
            provider_profiles,
            secrets,
            store=self.store,
        )
        self.provider_profiles = provider_profiles
        self.connector_id = connector_id
        self.breakers: dict[str, CircuitBreaker] = {}
        self.inbound_messages: asyncio.Queue[Message] = asyncio.Queue()
        self.inbound_tasks: asyncio.Queue[Task] = asyncio.Queue()
        self.outbound_actions: asyncio.Queue[OutboundWebhookAction] = asyncio.Queue()
        self.dead_letter: list[dict[str, Any]] = []
        self._outbound_sender = outbound_sender
        self._stop_event = asyncio.Event()

    def _topic_inbound(self) -> list[Topic]:
        return [Topic(namespace="bridge.webhook.inbound", attributes={"connector": self.connector_id})]

    def _topic_outbound(self) -> Topic:
        return Topic(namespace="bridge.webhook.outbound", attributes={"connector": self.connector_id})

    def _breaker_for(self, target: str) -> CircuitBreaker:
        if target not in self.breakers:
            self.breakers[target] = CircuitBreaker()
        return self.breakers[target]

    def _record_dead_letter(self, action: OutboundWebhookAction, error: str) -> None:
        record = {"action": asdict(action), "error": error, "ts": time.time()}
        self.dead_letter.append(record)
        self.store.put(f"webhook:dead_letter:{uuid.uuid4()}", record)
        self.metrics.inc("webhook_dead_letter_total")

    def _translate_inbound(self, event: InboundWebhookEvent, profile: ProviderProfile) -> Message | Task:
        if profile.emit_as == "task":
            return Task(
                objective={"type": "webhook_event", "provider": event.provider},
                inputs={"event": asdict(event)},
            )
        payload = {"type": "webhook_event", "event": asdict(event)}
        return Message(
            sender=self.connector_id,
            topics=self._topic_inbound(),
            payload=payload,
        )

    async def accept_inbound_http(
        self,
        provider: str,
        *,
        method: str,
        headers: dict[str, str],
        raw_body: bytes,
        remote_addr: str | None = None,
        client_cert_present: bool = False,
    ) -> tuple[int, dict[str, str], bytes]:
        try:
            profile, payload, event_id, ts = self.security.validate_and_extract(
                provider,
                method=method,
                headers=headers,
                raw_body=raw_body,
                remote_addr=remote_addr,
                client_cert_present=client_cert_present,
            )
            event = InboundWebhookEvent(
                provider=provider,
                source=str(payload.get(profile.source_field, provider)),
                event_id=event_id,
                occurred_at=ts,
                subject=str(payload.get(profile.subject_field, "")),
                payload=payload,
                headers={k.lower(): v for k, v in headers.items()},
                trace_id=headers.get("X-Trace-Id") or headers.get("x-trace-id"),
            )
            translated = self._translate_inbound(event, profile)
            if isinstance(translated, Task):
                await self.inbound_tasks.put(translated)
            else:
                await self.inbound_messages.put(translated)
            self.metrics.inc("webhook_inbound_accepted_total")
            log_struct(
                logger,
                20,
                "webhook inbound accepted",
                provider=provider,
                event_id=event_id,
                trace_id=event.trace_id,
            )
            return 202, {"Content-Type": "application/json"}, b'{"status":"accepted"}'
        except WebhookSecurityError as e:
            self.metrics.inc("webhook_inbound_rejected_total")
            return 401, {"Content-Type": "application/json"}, json.dumps({"error": str(e)}).encode("utf-8")
        except Exception as e:
            self.metrics.inc("webhook_inbound_error_total")
            return 500, {"Content-Type": "application/json"}, json.dumps({"error": str(e)}).encode("utf-8")

    async def submit_outbound_action(self, action: OutboundWebhookAction) -> None:
        await self.outbound_actions.put(action)

    async def submit_outbound_message(self, message: Message) -> None:
        if not message.topics:
            return
        routing = next((t for t in message.topics if t.namespace == "bridge.webhook.outbound"), None)
        if routing is None:
            return
        attrs = routing.attributes or {}
        target = str(attrs.get("target", "default"))
        method = str(attrs.get("method", "POST"))
        url = str(attrs.get("url", ""))
        if not url:
            return
        deadline_raw = attrs.get("deadline")
        action = OutboundWebhookAction(
            target=target,
            method=method,
            url=url,
            body=message.payload,
            headers={k: str(v) for k, v in attrs.get("headers", {}).items()} if isinstance(attrs.get("headers"), dict) else {},
            idempotency_key=str(attrs.get("idempotency_key")) if attrs.get("idempotency_key") is not None else None,
            deadline=float(deadline_raw) if deadline_raw is not None else None,
        )
        await self.submit_outbound_action(action)

    def _default_outbound_sender(self, action: OutboundWebhookAction) -> tuple[int, bytes]:
        body = json.dumps(action.body, separators=(",", ":")).encode("utf-8")
        headers = {"Content-Type": "application/json", **action.headers}
        if action.idempotency_key:
            headers["Idempotency-Key"] = action.idempotency_key
        req = urllib.request.Request(
            action.url,
            method=action.method.upper(),
            data=body,
            headers=headers,
        )
        timeout = self.retry_policy.request_timeout_sec
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            return int(resp.status), data

    async def _send_outbound_once(self, action: OutboundWebhookAction) -> tuple[int, bytes]:
        sender = self._outbound_sender or self._default_outbound_sender
        if inspect.iscoroutinefunction(sender):
            return await sender(action)
        return await asyncio.to_thread(sender, action)

    async def dispatch_outbound_action(self, action: OutboundWebhookAction) -> bool:
        breaker = self._breaker_for(action.target)
        if breaker.is_open and not breaker.allow_request():
            self.metrics.inc("webhook_outbound_circuit_open_total")
            self._record_dead_letter(action, "circuit open")
            return False
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            if action.deadline is not None and time.time() > action.deadline:
                self._record_dead_letter(action, "deadline exceeded")
                return False
            try:
                status, _ = await self._send_outbound_once(action)
                if 200 <= status < 300:
                    breaker.record_success()
                    self.metrics.inc("webhook_outbound_sent_total")
                    return True
                breaker.record_failure()
                self.metrics.inc("webhook_outbound_retry_total")
                if attempt < self.retry_policy.max_attempts:
                    await asyncio.sleep(self.retry_policy.compute_delay(attempt))
            except (TimeoutError, urllib.error.URLError, OSError, ValueError) as e:
                breaker.record_failure()
                self.metrics.inc("webhook_outbound_retry_total")
                if attempt >= self.retry_policy.max_attempts:
                    self._record_dead_letter(action, str(e))
                    return False
                await asyncio.sleep(self.retry_policy.compute_delay(attempt))
            except Exception as e:
                breaker.record_failure()
                self._record_dead_letter(action, str(e))
                return False
        self._record_dead_letter(action, "max retries exceeded")
        return False

    async def run_outbound_dispatcher(self, *, poll_interval_sec: float = 0.1) -> None:
        self._stop_event.clear()
        while not self._stop_event.is_set():
            try:
                action = await asyncio.wait_for(self.outbound_actions.get(), timeout=poll_interval_sec)
            except TimeoutError:
                continue
            await self.dispatch_outbound_action(action)

    def stop_dispatcher(self) -> None:
        self._stop_event.set()
