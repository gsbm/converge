from __future__ import annotations

import json
from typing import Any

from converge.observability.metrics import MetricsCollector

from .connector import WebhookConnector
from .models import OutboundWebhookAction


class WebhookGateway:
    """
    HTTP-oriented facade around WebhookConnector.
    """

    def __init__(self, connector: WebhookConnector):
        self.connector = connector
        self.metrics: MetricsCollector = connector.metrics
        self._ready = True

    def is_healthy(self) -> bool:
        return True

    def is_ready(self) -> bool:
        return self._ready

    async def handle_post(
        self,
        provider: str,
        *,
        headers: dict[str, str],
        body: bytes,
        remote_addr: str | None = None,
        client_cert_present: bool = False,
    ) -> tuple[int, dict[str, str], bytes]:
        return await self.connector.accept_inbound_http(
            provider,
            method="POST",
            headers=headers,
            raw_body=body,
            remote_addr=remote_addr,
            client_cert_present=client_cert_present,
        )

    async def handle_outbound_payload(self, payload: dict[str, Any]) -> tuple[int, bytes]:
        try:
            action = OutboundWebhookAction(
                target=str(payload["target"]),
                method=str(payload.get("method", "POST")),
                url=str(payload["url"]),
                body=payload.get("body", {}),
                headers={k: str(v) for k, v in payload.get("headers", {}).items()}
                if isinstance(payload.get("headers"), dict)
                else {},
                idempotency_key=str(payload["idempotency_key"]) if "idempotency_key" in payload else None,
                deadline=float(payload["deadline"]) if "deadline" in payload else None,
            )
        except Exception as e:
            return 400, json.dumps({"error": f"invalid outbound payload: {e}"}).encode("utf-8")
        await self.connector.submit_outbound_action(action)
        return 202, b'{"status":"queued"}'

    def health_payload(self) -> bytes:
        return json.dumps({"status": "ok"}).encode("utf-8")

    def ready_payload(self) -> bytes:
        status = "ready" if self.is_ready() else "not_ready"
        return json.dumps({"status": status}).encode("utf-8")

    def metrics_payload(self) -> bytes:
        return self.metrics.format_prometheus().encode("utf-8")
