"""CLI for converge agent runtime."""

import argparse
import asyncio
import contextlib
import logging
import os
from pathlib import Path

from converge.core.agent import Agent
from converge.core.identity import Identity
from converge.network.transport.local import LocalTransport
from converge.runtime.loop import AgentRuntime


def _load_config(path: str | None) -> dict:
    """Load config from file (YAML or TOML) or env vars."""
    config: dict = {}
    # Env vars
    for key in ("transport", "host", "port", "config"):
        env_key = f"CONVERGE_{key.upper()}"
        val = os.environ.get(env_key)
        if val is not None:
            config[key] = val
    # File
    if path:
        p = Path(path)
        if p.exists():
            suffix = p.suffix.lower()
            if suffix in (".yaml", ".yml"):
                try:
                    import yaml
                    with p.open() as f:
                        file_config = yaml.safe_load(f)
                    if isinstance(file_config, dict):
                        config = {**config, **file_config}
                except ImportError:
                    pass
            elif suffix == ".toml":
                try:
                    import tomllib
                    with p.open("rb") as f:
                        file_config = tomllib.load(f)
                    if isinstance(file_config, dict):
                        config = {**config, **file_config}
                except ImportError:
                    pass
    return config


def main() -> None:
    """Entry point for converge CLI."""
    parser = argparse.ArgumentParser(prog="converge", description="Converge agent runtime")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run an agent")
    run_parser.add_argument(
        "-c", "--config",
        help="Config file path (YAML or TOML)",
        default=os.environ.get("CONVERGE_CONFIG"),
    )
    run_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.command == "run":
        _load_config(args.config)
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG)

        identity = Identity.generate()
        agent = Agent(identity)
        transport = LocalTransport(agent.id)

        runtime = AgentRuntime(agent=agent, transport=transport)

        async def _run() -> None:
            await runtime.start()
            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            finally:
                await runtime.stop()

        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(_run())


if __name__ == "__main__":
    main()
