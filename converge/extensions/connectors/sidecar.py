from __future__ import annotations

import argparse
import asyncio
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from converge.observability.logging import configure_logging, get_logger

from .connector import WebhookConnector
from .gateway import WebhookGateway
from .retry import WebhookRetryPolicy
from .security import ProviderProfile, WebhookSecurityPolicy

logger = get_logger(__name__)


class _GatewayHandler(BaseHTTPRequestHandler):
    gateway: WebhookGateway
    loop: asyncio.AbstractEventLoop

    def _write(self, status: int, body: bytes, *, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            self._write(200, self.gateway.health_payload(), content_type="application/json")
            return
        if parsed.path == "/readyz":
            status = 200 if self.gateway.is_ready() else 503
            self._write(status, self.gateway.ready_payload(), content_type="application/json")
            return
        if parsed.path == "/metrics":
            self._write(200, self.gateway.metrics_payload(), content_type="text/plain; version=0.0.4")
            return
        self._write(404, b'{"error":"not found"}', content_type="application/json")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        if parsed.path.startswith("/webhook/"):
            provider = parsed.path.split("/webhook/", 1)[1]
            fut = asyncio.run_coroutine_threadsafe(
                self.gateway.handle_post(
                    provider,
                    headers=dict(self.headers.items()),
                    body=body,
                    remote_addr=self.client_address[0] if self.client_address else None,
                ),
                self.loop,
            )
            status, headers, out = fut.result()
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
            return
        if parsed.path == "/outbound":
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                self._write(400, b'{"error":"invalid json"}', content_type="application/json")
                return
            fut = asyncio.run_coroutine_threadsafe(self.gateway.handle_outbound_payload(payload), self.loop)
            status, out = fut.result()
            self._write(status, out, content_type="application/json")
            return
        self._write(404, b'{"error":"not found"}', content_type="application/json")

    def log_message(self, msg_fmt: str, *args) -> None:
        logger.debug("%s - %s", self.address_string(), msg_fmt % args)


def run_webhook_sidecar(
    *,
    bind: str,
    port: int,
    provider_profiles: dict[str, ProviderProfile],
    secrets: dict[str, str],
    security_policy: WebhookSecurityPolicy | None = None,
    retry_policy: WebhookRetryPolicy | None = None,
) -> None:
    connector = WebhookConnector(
        provider_profiles=provider_profiles,
        secrets=secrets,
        security_policy=security_policy,
        retry_policy=retry_policy,
    )
    gateway = WebhookGateway(connector)

    loop = asyncio.new_event_loop()
    _GatewayHandler.gateway = gateway
    _GatewayHandler.loop = loop

    def loop_main() -> None:
        asyncio.set_event_loop(loop)
        loop.create_task(connector.run_outbound_dispatcher())
        loop.run_forever()

    t = threading.Thread(target=loop_main, daemon=True)
    t.start()

    httpd = ThreadingHTTPServer((bind, port), _GatewayHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        connector.stop_dispatcher()
        loop.call_soon_threadsafe(loop.stop)
        t.join(timeout=2)
        httpd.server_close()


def _load_sidecar_config(path: str) -> tuple[dict[str, ProviderProfile], dict[str, str], str, int]:
    with Path(path).open("rb") as f:
        if path.endswith(".toml"):
            import tomllib

            cfg = tomllib.load(f)
        else:
            cfg = json.loads(f.read().decode("utf-8"))
    bind = str(cfg.get("bind", "127.0.0.1"))
    port = int(cfg.get("port", 8090))
    providers: dict[str, ProviderProfile] = {}
    for p in cfg.get("providers", []):
        profile = ProviderProfile(
            name=str(p["name"]),
            secret_ref=str(p["secret_ref"]),
            signature_header=str(p.get("signature_header", "X-Webhook-Signature")),
            timestamp_header=str(p.get("timestamp_header", "X-Webhook-Timestamp")),
            event_id_field=str(p.get("event_id_field", "event_id")),
            signature_algorithm=str(p.get("signature_algorithm", "sha256")),
            canonicalization=str(p.get("canonicalization", "raw_body")),
            required_payload_fields=tuple(p.get("required_payload_fields", [])),
            subject_field=str(p.get("subject_field", "subject")),
            source_field=str(p.get("source_field", "source")),
            emit_as=str(p.get("emit_as", "message")),
        )
        providers[profile.name] = profile
    secrets = {str(k): str(v) for k, v in cfg.get("secrets", {}).items()}
    return providers, secrets, bind, port


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="converge-webhook-sidecar")
    parser.add_argument("--config", required=True, help="Path to sidecar JSON/TOML config")
    parser.add_argument("--json-logs", action="store_true")
    args = parser.parse_args(argv)
    configure_logging(logging.INFO, json_format=args.json_logs)
    providers, secrets, bind, port = _load_sidecar_config(args.config)
    run_webhook_sidecar(bind=bind, port=port, provider_profiles=providers, secrets=secrets)
