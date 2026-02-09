# CLI and configuration

The converge CLI runs an agent process with configurable transport and logging. Configuration is read from environment variables and, optionally, a file (YAML or TOML). The CLI entrypoint is installed when the package is installed; YAML support requires the `cli` extra.

## Entrypoint

```bash
converge <command> [options]
```

Commands:

- **`run`**: Start an agent with a generated identity, local transport, and a long-running loop until interrupted.

Options for `run`:

- **`-c` / `--config`**: Path to a config file (YAML or TOML). Default: value of `CONVERGE_CONFIG` if set.
- **`-v` / `--verbose`**: Enable DEBUG-level logging.

Example:

```bash
converge run
converge run -c config.yaml -v
```

## Environment variables

Configuration keys can be set via environment variables. Names follow the pattern `CONVERGE_<KEY>` with `<KEY>` in uppercase:

| Variable | Purpose |
|----------|---------|
| `CONVERGE_TRANSPORT` | Transport type (e.g. `local`); used when wiring the runtime in future versions. |
| `CONVERGE_HOST` | Host for network transports. |
| `CONVERGE_PORT` | Port for network transports. |
| `CONVERGE_CONFIG` | Default config file path (same as `-c`). |

File-based config is merged with env: env values are overridden by the config file when both specify the same key.

## Config file format

Supported formats: **YAML** (`.yaml`, `.yml`) and **TOML** (`.toml`). YAML parsing requires `pyyaml` (install with `converge[cli]`). TOML uses the standard library `tomllib` (Python 3.11+).

The file must evaluate to a single mapping (dict). Keys are merged into the configuration dict; typical keys include `transport`, `host`, `port`, and any custom keys your setup uses.

Example YAML:

```yaml
transport: local
# host: 127.0.0.1
# port: 9000
```

Example TOML:

```toml
transport = "local"
# host = "127.0.0.1"
# port = 9000
```

## Current run behavior

With `converge run`, the process:

1. Loads config (env + optional file).
2. Sets logging level to DEBUG if `-v` is used.
3. Generates a new identity and creates a default `Agent` and `LocalTransport`.
4. Builds an `AgentRuntime`, starts it, then runs an infinite loop (sleep 1s) until KeyboardInterrupt.
5. On interrupt, stops the runtime cleanly.

No pool manager, task manager, or discovery store are wired by default; the agent runs with the minimal loop and local transport only. To use TCP, custom transports, or persistence, use the Python API (see [Quick start](quickstart.md) and [API reference](../api/index.md)).
