"""Tests for converge.cli and converge.__main__."""

import os
from unittest.mock import patch

from converge.cli import _load_config, main


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
    cfg = _load_config(None)
    assert cfg.get("transport") == "local"
    del os.environ["CONVERGE_TRANSPORT"]


def test_main_module():
    with patch("converge.cli.main") as mock_main:
        import converge.__main__

        converge.__main__.main()
        mock_main.assert_called_once()
