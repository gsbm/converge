"""Tests for converge.cli and converge.__main__."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from converge.cli import _create_transport, _load_config, _validate_config, main


def test_cli_main_run():
    import sys

    with patch.object(sys, "argv", ["converge", "run"]), patch("converge.cli.asyncio.run") as mock_run:
        def run_fake(coro):
            coro.close()

        mock_run.side_effect = run_fake
        main()
        mock_run.assert_called_once()


def test_cli_load_config_env():
    os.environ["CONVERGE_TRANSPORT"] = "local"
    try:
        cfg = _load_config(None)
        assert cfg.get("transport") == "local"
    finally:
        os.environ.pop("CONVERGE_TRANSPORT", None)


def test_cli_load_config_env_agents_port_pool_discovery():
    os.environ["CONVERGE_AGENTS"] = "3"
    os.environ["CONVERGE_PORT"] = "9999"
    os.environ["CONVERGE_POOL_ID"] = "my-pool"
    os.environ["CONVERGE_DISCOVERY_STORE"] = "memory"
    try:
        cfg = _load_config(None)
        assert cfg.get("agents") == 3
        assert cfg.get("port") == 9999
        assert cfg.get("pool_id") == "my-pool"
        assert cfg.get("discovery_store") == "memory"
    finally:
        for k in ("CONVERGE_AGENTS", "CONVERGE_PORT", "CONVERGE_POOL_ID", "CONVERGE_DISCOVERY_STORE"):
            os.environ.pop(k, None)


def test_cli_load_config_file_yaml():
    import importlib.util

    if importlib.util.find_spec("yaml") is None:
        pytest.skip("pyyaml not available")
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        f.write(b"transport: tcp\nhost: 0.0.0.0\nport: 9000\nagents: 2\n")
        f.flush()
        path = f.name
    try:
        cfg = _load_config(path)
        assert cfg.get("transport") == "tcp"
        assert cfg.get("host") == "0.0.0.0"
        assert cfg.get("port") == 9000
        assert cfg.get("agents") == 2
    finally:
        Path(path).unlink(missing_ok=True)


def test_cli_load_config_file_toml():
    import importlib.util

    if importlib.util.find_spec("tomllib") is None:
        pytest.skip("tomllib not available")
    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
        f.write(b'transport = "websocket"\nport = 7000\n')
        f.flush()
        path = f.name
    try:
        cfg = _load_config(path)
        assert cfg.get("transport") == "websocket"
        assert cfg.get("port") == 7000
    finally:
        Path(path).unlink(missing_ok=True)


def test_create_transport_local():
    from converge.network.transport.local import LocalTransport
    t = _create_transport("local", "agent-1", "127.0.0.1", 8888)
    assert isinstance(t, LocalTransport)


def test_create_transport_tcp():
    from converge.network.transport.tcp import TcpTransport
    t = _create_transport("tcp", "agent-1", "127.0.0.1", 8888)
    assert isinstance(t, TcpTransport)
    assert t.port == 8888


def test_main_module():
    with patch("converge.cli.main") as mock_main:
        import converge.__main__

        converge.__main__.main()
        mock_main.assert_called_once()


def test_validate_config_rejects_invalid_port():
    """Invalid config (e.g. port as string 'abc') raises ValueError with a clear message."""
    with pytest.raises(ValueError, match="Invalid configuration"):
        _validate_config({"port": "abc"})
    with pytest.raises(ValueError, match="Invalid configuration"):
        _validate_config({"agents": "not-a-number"})


def test_validate_config_accepts_valid_config():
    _validate_config({})
    _validate_config({"transport": "local", "port": 8888, "agents": 2})
    _validate_config({"port": 9999, "pool_id": "p1", "discovery_store": "memory"})


def test_validate_config_allows_unknown_keys():
    """Unknown keys are allowed (backward compatibility)."""
    _validate_config({"unknown_key": 42, "port": 8888})
