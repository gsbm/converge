import asyncio
import hashlib
import hmac
import json
import time

import pytest

from converge.core.message import Message
from converge.core.topic import Topic
from converge.extensions.connectors import (
    OutboundWebhookAction,
    ProviderProfile,
    WebhookConnector,
    WebhookGateway,
    WebhookRetryPolicy,
    WebhookSecurityPolicy,
)


def _signed_headers(secret: str, body: bytes, ts: float | None = None) -> dict[str, str]:
    ts_val = ts if ts is not None else time.time()
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-Webhook-Timestamp": str(ts_val),
        "X-Webhook-Signature": sig,
    }


def _connector(*, required_fields=(), emit_as="message", sender=None) -> WebhookConnector:
    profile = ProviderProfile(
        name="acme",
        secret_ref="acme_secret",
        required_payload_fields=tuple(required_fields),
        emit_as=emit_as,
    )
    return WebhookConnector(
        provider_profiles={"acme": profile},
        secrets={"acme_secret": "secret-1"},
        security_policy=WebhookSecurityPolicy(strict_mode=True),
        retry_policy=WebhookRetryPolicy(max_attempts=3, base_delay_sec=0.001, max_delay_sec=0.005, jitter_ratio=0.0),
        outbound_sender=sender,
    )


@pytest.mark.asyncio
async def test_inbound_accepts_valid_signature_and_enqueues_message():
    c = _connector(required_fields=("subject",))
    body = json.dumps({"event_id": "e1", "subject": "hello", "source": "ext"}).encode("utf-8")
    status, _, _ = await c.accept_inbound_http(
        "acme",
        method="POST",
        headers=_signed_headers("secret-1", body),
        raw_body=body,
    )
    assert status == 202
    msg = await asyncio.wait_for(c.inbound_messages.get(), timeout=0.1)
    assert isinstance(msg, Message)
    assert msg.topics[0].namespace == "bridge.webhook.inbound"


@pytest.mark.asyncio
async def test_inbound_emit_as_task():
    c = _connector(required_fields=("subject",), emit_as="task")
    body = json.dumps({"event_id": "e2", "subject": "hello"}).encode("utf-8")
    status, _, _ = await c.accept_inbound_http(
        "acme",
        method="POST",
        headers=_signed_headers("secret-1", body),
        raw_body=body,
    )
    assert status == 202
    task = await asyncio.wait_for(c.inbound_tasks.get(), timeout=0.1)
    assert task.objective["type"] == "webhook_event"


@pytest.mark.asyncio
async def test_inbound_rejects_unknown_provider():
    c = _connector()
    body = json.dumps({"event_id": "e1"}).encode("utf-8")
    status, _, _ = await c.accept_inbound_http(
        "unknown",
        method="POST",
        headers=_signed_headers("secret-1", body),
        raw_body=body,
    )
    assert status == 401


@pytest.mark.asyncio
async def test_inbound_rejects_stale_timestamp():
    c = _connector()
    old_ts = time.time() - 10_000
    body = json.dumps({"event_id": "e1"}).encode("utf-8")
    status, _, _ = await c.accept_inbound_http(
        "acme",
        method="POST",
        headers=_signed_headers("secret-1", body, ts=old_ts),
        raw_body=body,
    )
    assert status == 401


@pytest.mark.asyncio
async def test_inbound_rejects_duplicate_event_id():
    c = _connector()
    body = json.dumps({"event_id": "dup"}).encode("utf-8")
    headers = _signed_headers("secret-1", body)
    first, _, _ = await c.accept_inbound_http("acme", method="POST", headers=headers, raw_body=body)
    second, _, _ = await c.accept_inbound_http("acme", method="POST", headers=headers, raw_body=body)
    assert first == 202
    assert second == 401


@pytest.mark.asyncio
async def test_inbound_rejects_missing_required_field():
    c = _connector(required_fields=("subject",))
    body = json.dumps({"event_id": "e1"}).encode("utf-8")
    status, _, _ = await c.accept_inbound_http(
        "acme",
        method="POST",
        headers=_signed_headers("secret-1", body),
        raw_body=body,
    )
    assert status == 401


@pytest.mark.asyncio
async def test_outbound_retries_then_succeeds():
    calls = {"n": 0}

    def sender(action):
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError("timeout")
        return 200, b"ok"

    c = _connector(sender=sender)
    ok = await c.dispatch_outbound_action(
        action=OutboundWebhookAction(
            target="t1",
            method="POST",
            url="http://example.com",
            body={"x": 1},
        ),
    )
    assert ok is True
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_outbound_circuit_breaker_dead_letters_when_open():
    def sender(_action):
        raise TimeoutError("always fails")

    c = _connector(sender=sender)
    action = OutboundWebhookAction(
        target="t1",
        method="POST",
        url="http://example.com",
        body={"x": 1},
    )
    c.breakers["t1"] = c._breaker_for("t1")
    c.breakers["t1"].failure_threshold = 1
    await c.dispatch_outbound_action(action)
    c.breakers["t1"].record_failure()
    ok = await c.dispatch_outbound_action(action)
    assert ok is False
    assert c.dead_letter


@pytest.mark.asyncio
async def test_submit_outbound_message_converts_to_action():
    c = _connector()
    msg = Message(
        sender="a1",
        topics=[
            Topic(
                "bridge.webhook.outbound",
                {
                    "target": "acme-out",
                    "method": "POST",
                    "url": "http://example.com/hook",
                    "headers": {"X-Test": "1"},
                },
            ),
        ],
        payload={"ok": True},
    )
    await c.submit_outbound_message(msg)
    action = await asyncio.wait_for(c.outbound_actions.get(), timeout=0.1)
    assert action.target == "acme-out"
    assert action.url.endswith("/hook")


@pytest.mark.asyncio
async def test_gateway_health_ready_metrics_endpoints():
    c = _connector()
    g = WebhookGateway(c)
    assert g.is_healthy() is True
    assert g.is_ready() is True
    assert b"status" in g.health_payload()
    assert b"status" in g.ready_payload()
    m = g.metrics_payload()
    assert isinstance(m, bytes)
