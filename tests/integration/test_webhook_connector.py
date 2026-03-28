import json
import time

import pytest

from converge.extensions.connectors import (
    OutboundWebhookAction,
    ProviderProfile,
    WebhookConnector,
    WebhookRetryPolicy,
)
from converge.extensions.storage.sqlite_store import SQLiteStore


def _sign(secret: str, body: bytes) -> str:
    import hashlib
    import hmac

    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_shared_store_idempotency_across_connectors(tmp_path):
    store = SQLiteStore(path=tmp_path / "wh.sqlite3")
    profiles = {"acme": ProviderProfile(name="acme", secret_ref="s1")}
    secrets = {"s1": "shared-secret"}
    c1 = WebhookConnector(provider_profiles=profiles, secrets=secrets, store=store)
    c2 = WebhookConnector(provider_profiles=profiles, secrets=secrets, store=store)

    body = json.dumps({"event_id": "evt-1"}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Timestamp": str(time.time()),
        "X-Webhook-Signature": _sign("shared-secret", body),
    }
    s1, _, _ = await c1.accept_inbound_http("acme", method="POST", headers=headers, raw_body=body)
    s2, _, _ = await c2.accept_inbound_http("acme", method="POST", headers=headers, raw_body=body)
    assert s1 == 202
    assert s2 == 401
    msg = await c1.inbound_messages.get()
    assert msg.topics[0].namespace == "bridge.webhook.inbound"


@pytest.mark.asyncio
async def test_outbound_retries_and_dead_letter():
    attempts = {"n": 0}

    def sender(_action):
        attempts["n"] += 1
        raise TimeoutError("timeout")

    connector = WebhookConnector(
        provider_profiles={"acme": ProviderProfile(name="acme", secret_ref="s1")},
        secrets={"s1": "sec"},
        retry_policy=WebhookRetryPolicy(max_attempts=3, base_delay_sec=0.001, max_delay_sec=0.005, jitter_ratio=0.0),
        outbound_sender=sender,
    )
    ok = await connector.dispatch_outbound_action(
        OutboundWebhookAction(
            target="t1",
            method="POST",
            url="http://example.com/webhook",
            body={"x": 1},
        ),
    )
    assert ok is False
    assert attempts["n"] == 3
    assert connector.dead_letter
