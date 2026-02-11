"""CLI for converge agent runtime.

Supports configurable transport (local, tcp), multiple agents in one process,
optional pool and discovery store. Config keys: transport, host, port, agents,
pool_id, discovery_store (path or 'memory').
"""

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
    """Load config from file (YAML or TOML) or env vars.

    Reads transport, host, port, config, agents, pool_id, discovery_store
    from CONVERGE_* env vars and from the config file.
    """
    config: dict = {}
    for key in ("transport", "host", "port", "config", "agents", "pool_id", "discovery_store"):
        env_key = f"CONVERGE_{key.upper()}"
        val = os.environ.get(env_key)
        if val is not None:
            if key == "port" or key == "agents":
                with contextlib.suppress(ValueError):
                    val = int(val)
            config[key] = val
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
    if "port" in config and not isinstance(config["port"], int):
        try:
            config["port"] = int(config["port"])
        except (ValueError, TypeError):
            config["port"] = 8888
    if "agents" in config and not isinstance(config["agents"], int):
        try:
            config["agents"] = int(config["agents"])
        except (ValueError, TypeError):
            config["agents"] = 1
    return config


def _create_transport(transport_type: str, agent_id: str, host: str, port: int):
    """Create a transport instance from config."""
    if transport_type == "tcp":
        from converge.network.transport.tcp import TcpTransport
        return TcpTransport(host=host, port=port, identity_fingerprint=agent_id)
    return LocalTransport(agent_id)


def main() -> None:
    """Entry point for converge CLI."""
    parser = argparse.ArgumentParser(prog="converge", description="Converge agent runtime")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run one or more agents")
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
        config = _load_config(args.config)
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG)

        transport_type = (config.get("transport") or "local").lower()
        host = config.get("host") or "127.0.0.1"
        port = config.get("port") or 8888
        num_agents = max(1, int(config.get("agents") or 1))
        pool_id = config.get("pool_id")
        discovery_store_path = config.get("discovery_store")

        store = None
        discovery_service = None
        if discovery_store_path and discovery_store_path.lower() != "memory":
            from converge.extensions.storage.file import FileStore
            store = FileStore(base_path=discovery_store_path)
        elif discovery_store_path:
            from converge.extensions.storage.memory import MemoryStore
            store = MemoryStore()

        if store is not None:
            from converge.network.discovery import DiscoveryService
            discovery_service = DiscoveryService(store=store)

        pool_manager = None
        task_manager = None
        pool = None
        if num_agents > 1 or pool_id:
            from converge.coordination.pool_manager import PoolManager
            from converge.coordination.task_manager import TaskManager
            from converge.extensions.storage.memory import MemoryStore
            pool_manager = PoolManager(store=MemoryStore())
            task_manager = TaskManager(store=MemoryStore())
            if pool_id:
                pool = pool_manager.create_pool({"id": pool_id})

        runtimes = []
        for i in range(num_agents):
            identity = Identity.generate()
            agent = Agent(identity)
            agent_port = port + i if transport_type == "tcp" and num_agents > 1 else port
            transport = _create_transport(transport_type, agent.id, host, agent_port)
            agent_descriptor = None
            if discovery_service is not None:
                from converge.network.network import build_descriptor
                agent_descriptor = build_descriptor(agent)
            runtime = AgentRuntime(
                agent=agent,
                transport=transport,
                pool_manager=pool_manager,
                task_manager=task_manager,
                discovery_service=discovery_service,
                agent_descriptor=agent_descriptor,
            )
            runtimes.append(runtime)
            if pool is not None and pool_manager is not None:
                pool_manager.join_pool(agent.id, pool.id)

        async def _run() -> None:
            await asyncio.gather(*[r.start() for r in runtimes])
            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            finally:
                for r in runtimes:
                    await r.stop()

        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(_run())


if __name__ == "__main__":
    main()
