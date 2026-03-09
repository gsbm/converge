# Scaling and deployment

## Patterns

- **Single process, many agents:** Run one process with multiple agents (e.g. `converge run` with `agents: N`). All agents share the same PoolManager and TaskManager when pool is configured; discovery and pool/task state live in the chosen store (memory or file). Suitable for development and small deployments.

- **One process per agent:** Run one process per agent, each with its own runtime. Use a **shared store** (e.g. Redis, SQLite, or a database) for PoolManager, TaskManager, and DiscoveryService so all processes see the same pools and tasks. Connect processes via TCP or WebSocket transport; ensure discovery and identity registry are populated so agents can find and verify each other.

- **N processes × M agents with shared store:** Scale out by running multiple processes; each process can host one or more agents. Pool and task state live in the store, so multi-process coordination works as long as every node uses the same store and discovery. For multiple physical nodes, run multiple processes (one per node or more), connect them via TCP/WebSocket, and use a shared discovery store (e.g. Redis or a DB). No built-in leader election; use external orchestration (e.g. Kubernetes) for process lifecycle.

**Multi-process discovery:** When using a shared store for discovery, each process has its own `DiscoveryService(store=shared_store)`. To see agents registered by other processes, call `query` with descriptors from the store: use `query(query, refresh_from_store=True)` to reload from store before filtering, or pass `candidates=None` to use the service's in-memory descriptors (loaded at init). Example:

```python
discovery = DiscoveryService(store=shared_store)
results = discovery.query(query, refresh_from_store=True)  # latest from store
```

## converge run

The `converge run` CLI starts **one process**. For multiple nodes, run `converge run` (or your own entrypoint) on each node with the same pool_id and discovery_store path (or shared backend). Configure transport (e.g. TCP host/port) so agents can reach each other.
