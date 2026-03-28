"""Tests for converge.observability.runtime_ops."""

import json
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from converge.observability.metrics import MetricsCollector
from converge.observability.runtime_ops import RuntimeOpsServer


class _Runtime:
    def __init__(self, *, healthy: bool = True, ready: bool = True):
        self._healthy = healthy
        self._ready = ready

    def is_healthy(self) -> bool:
        return self._healthy

    def is_ready(self) -> bool:
        return self._ready


def _fetch(url: str) -> tuple[int, str]:
    with urlopen(url, timeout=1.0) as resp:  # noqa: S310
        return resp.status, resp.read().decode("utf-8")


def _start_or_skip(server: RuntimeOpsServer) -> None:
    try:
        server.start()
    except PermissionError:
        pytest.skip("HTTP socket bind not permitted in this environment")


def test_runtime_ops_server_endpoints():
    runtime = _Runtime()
    metrics = MetricsCollector()
    metrics.inc("messages_sent", 2)
    metrics.gauge("pool_size", 3.0)
    server = RuntimeOpsServer(runtime, metrics, host="127.0.0.1", port=0)
    _start_or_skip(server)
    try:
        host, port = server.address or ("127.0.0.1", 0)
        status_h, body_h = _fetch(f"http://{host}:{port}/health")
        assert status_h == 200
        assert json.loads(body_h)["status"] == "ok"

        status_r, body_r = _fetch(f"http://{host}:{port}/ready")
        assert status_r == 200
        assert json.loads(body_r)["status"] == "ready"

        status_m, body_m = _fetch(f"http://{host}:{port}/metrics")
        assert status_m == 200
        assert "messages_sent 2" in body_m
        assert "pool_size 3.0" in body_m
    finally:
        server.stop()


def test_runtime_ops_server_unhealthy_unready():
    runtime = _Runtime(healthy=False, ready=False)
    server = RuntimeOpsServer(runtime, host="127.0.0.1", port=0)
    _start_or_skip(server)
    try:
        host, port = server.address or ("127.0.0.1", 0)
        with pytest.raises(HTTPError) as health_exc:
            _fetch(f"http://{host}:{port}/health")
        assert health_exc.value.code == 503
        with pytest.raises(HTTPError) as ready_exc:
            _fetch(f"http://{host}:{port}/ready")
        assert ready_exc.value.code == 503
    finally:
        server.stop()
