from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from converge.observability.metrics import MetricsCollector


class RuntimeOpsServer:
    def __init__(
        self,
        runtime,
        metrics_collector: MetricsCollector | None = None,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
    ) -> None:
        self.runtime = runtime
        self.metrics_collector = metrics_collector
        self.host = host
        self.port = port
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def address(self) -> tuple[str, int] | None:
        if self._httpd is None:
            return None
        return self._httpd.server_address  # type: ignore[return-value]

    def start(self) -> None:
        if self._httpd is not None:
            return
        handler = self._build_handler()
        self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd is None:
            return
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._httpd = None
        self._thread = None

    def _build_handler(self):
        runtime = self.runtime
        metrics = self.metrics_collector

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                path = urlparse(self.path).path
                if path == "/health":
                    status = 200 if runtime.is_healthy() else 503
                    self._write(status, {"status": "ok" if status == 200 else "unhealthy"})
                    return
                if path == "/ready":
                    status = 200 if runtime.is_ready() else 503
                    self._write(status, {"status": "ready" if status == 200 else "not_ready"})
                    return
                if path == "/metrics":
                    body = metrics.format_prometheus() if metrics is not None else ""
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; version=0.0.4")
                    self.send_header("Content-Length", str(len(body.encode("utf-8"))))
                    self.end_headers()
                    self.wfile.write(body.encode("utf-8"))
                    return
                self._write(404, {"error": "not found"})

            def _write(self, status: int, payload: dict) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args) -> None:
                return

        return Handler
