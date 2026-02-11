# CLI and configuration

The converge CLI runs one or more agent processes with configurable transport, pool, and discovery. Configuration is read from environment variables and, optionally, a file (YAML or TOML). The CLI entrypoint is installed when the package is installed; YAML support requires the `cli` extra.

## Entrypoint

```bash
converge <command> [options]
```

Commands:

- **`run`**: Start one or more agents with generated identities, optional transport (local or TCP), optional pool and discovery, and a long-running loop until interrupted.

Options for `run`:

- **`-c` / `--config`**: Path to a config file (YAML or TOML). Default: value of `CONVERGE_CONFIG` if set.
- **`-v` / `--verbose`**: Enable DEBUG-level logging.

Examples:

```bash
converge run
converge run -c config.yaml -v
```

## Environment variables

Configuration keys can be set via environment variables. Names follow the pattern `CONVERGE_<KEY>` with `<KEY>` in uppercase:

| Variable | Purpose |
|----------|---------|
| `CONVERGE_TRANSPORT` | Transport type: `local` (default) or `tcp`. |
| `CONVERGE_HOST` | Host for network transports (default `127.0.0.1`). |
| `CONVERGE_PORT` | Port for TCP transport (default `8888`). With multiple agents and TCP, each agent uses `port + index`. |
| `CONVERGE_AGENTS` | Number of agents to run in this process (default `1`). When > 1, a shared pool manager and task manager are created. |
| `CONVERGE_POOL_ID` | If set, a pool with this id is created and all agents join it. |
| `CONVERGE_DISCOVERY_STORE` | If set to `memory`, an in-memory discovery store is used and agents register on start; if a path, a file-based store is used. |
| `CONVERGE_CONFIG` | Default config file path (same as `-c`). |

File-based config is merged with env: file values override env when both specify the same key.

## Config file format

Supported formats: **YAML** (`.yaml`, `.yml`) and **TOML** (`.toml`). YAML parsing requires `pyyaml` (install with `converge[cli]`). TOML uses the standard library `tomllib` (Python 3.11+).

The file must evaluate to a single mapping (dict). Keys: `transport`, `host`, `port`, `agents`, `pool_id`, `discovery_store`.

Example YAML (multi-agent with pool and discovery):

```yaml
transport: local
agents: 3
pool_id: my-pool
discovery_store: memory
```

Example YAML (TCP, single agent):

```yaml
transport: tcp
host: 0.0.0.0
port: 9000
```

Example TOML:

```toml
transport = "tcp"
host = "127.0.0.1"
port = 8888
agents = 2
pool_id = "workers"
discovery_store = "memory"
```

## Run behavior

With `converge run`, the process:

1. Loads config (env + optional file).
2. Sets logging level to DEBUG if `-v` is used.
3. If `discovery_store` is set, creates a store (memory or file) and a `DiscoveryService`; each agent will register on start and unregister on stop.
4. If `agents` > 1 or `pool_id` is set, creates a shared `PoolManager` and `TaskManager`; if `pool_id` is set, creates that pool and joins all agents to it.
5. For each of `agents` (default 1): generates an identity, creates an `Agent` and transport (local or TCP with host/port), builds an `AgentDescriptor` when discovery is used, and constructs an `AgentRuntime` with pool_manager, task_manager, discovery_service, and agent_descriptor as appropriate.
6. Starts all runtimes with `asyncio.gather`, then runs until KeyboardInterrupt.
7. On interrupt, stops all runtimes cleanly.

To use WebSocket transport or custom persistence, use the Python API (see [Quick start](quickstart.md) and [API reference](../api/index.md)).
