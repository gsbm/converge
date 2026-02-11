# Design and module layout

## Design principles

1. **Agent-first:** Humans are tool-providers, not participants; all APIs assume machine actors. Agents are the only first-class actors.
2. **Low-level and composable:** The library provides primitives and clear interfaces; higher-level behaviors are built by composition. No hidden global state.
3. **Network-native:** Agents are peers; no central controller is required. Discovery and transport are pluggable.
4. **Task-oriented:** Interactions are modeled as task discovery, execution, coordination, or evaluation. Tasks and pools are explicit.
5. **Observable:** Message flows, task state, and decision points can be inspected via logging, tracing, metrics, and replay. No implicit “magic” state.

## Module structure

```
converge/
├── core/               # Identity, Agent, Message, Topic, Task, Pool, Capability, Store, Decisions
├── network/            # AgentNetwork, Discovery (AgentDescriptor, DiscoveryQuery, DiscoveryService),
│                       # IdentityRegistry, Transport (base, local, tcp, websocket)
├── coordination/       # PoolManager, TaskManager, NegotiationProtocol, Consensus, BiddingProtocol, DelegationProtocol
├── runtime/            # AgentRuntime, Inbox, Scheduler, Executor (Protocol), StandardExecutor
├── policy/             # Admission (Open, Whitelist, Token), TrustModel, Governance (Democratic, Dictatorial), Safety (ResourceLimits, ActionPolicy)
├── observability/      # Logging (JsonFormatter, configure_logging, get_logger, log_struct), Tracing, MetricsCollector, ReplayLog
├── extensions/         # Storage (memory, file), crypto (symmetric, kdf, random), llm (agent, openai, anthropic, mistral, base)
├── cli.py              # converge run; config from env and optional YAML/TOML
└── __main__.py         # Entrypoint that delegates to cli.main
```

## Runtime model

The agent execution loop (conceptually):

```
while running:
    wait_for_work(timeout)   # Scheduler: event or timeout
    messages = inbox.poll()
    tasks = task_manager.list_pending_tasks()  # if task_manager set
    decisions = agent.decide(messages, tasks)  # sync or async
    if executor: executor.execute(decisions)
    else: for d in decisions: _execute_decision_fallback(d)  # e.g. sign and send Message
```

- No hidden background threads; asyncio-driven.
- When a **discovery service** is supplied, the runtime registers the agent on start and unregisters on stop so peers can find it by topic/capability.
- **Inbox** buffers messages; supports bounded size and optional drop-when-full.
- **Executor** (when pool_manager and task_manager are set) handles SendMessage, SubmitTask, ClaimTask, JoinPool, LeavePool, CreatePool, ReportTask; unknown types are logged.
- **Fallback:** When no executor is configured, only message-like decisions are signed and sent on the transport; other types are no-ops.
- Backpressure and deterministic scheduling are the integrator’s responsibility where required.

## Transport layer

All transports implement the same interface:

- **`start()` / `stop()`**: Lifecycle.
- **`send(message: Message)`**: Send a message (routing is transport-specific).
- **`receive() -> Message`**: Receive one message (blocking until available).

Transports are hot-swappable and stateless from the runtime’s perspective. Implementations:

- **Local:** Singleton registry; delivery by recipient or by topic subscription; in-process only.
- **TCP:** Length-prefixed msgpack over TCP; topic-based routing (namespace `transport.tcp`, attributes host/port); connection pooling.
- **WebSocket:** Optional; see `converge[websocket]` and the network transport module.

**Identity registry:** Transports that support verification (e.g. local) can use an `IdentityRegistry` (fingerprint → public key) to implement `receive_verified()` and discard or reject messages that fail verification.

## State and persistence

- Agent state is explicit (no global mutable singletons for business state).
- **Store** abstraction: `put`, `get`, `delete`, `list(prefix)`. Used by PoolManager, TaskManager, and DiscoveryService when a store is supplied.
- **MemoryStore** and **FileStore** (extensions) provide in-memory and file-backed implementations. FileStore uses pickle and a directory per base path.

**Recovery:** Pool and task state are restored on restart by constructing PoolManager and TaskManager with the **same store** used before shutdown. Inbox and in-flight messages are best-effort (no persistence unless the transport supports replay). The runtime supports an optional **checkpoint_store** and **checkpoint_interval_sec** to write `agent_id -> last_activity_ts` for observability; this does not change processing order or replay.

## CLI

The CLI (`converge run`) can run one or more agents with configurable transport (local or TCP), optional pool and discovery store. Config is read from environment variables and, if the `cli` extra is installed, from an optional YAML or TOML file. Keys include `transport`, `host`, `port`, `agents`, `pool_id`, and `discovery_store`. See [CLI and configuration](../user_guide/cli_and_config.md).
