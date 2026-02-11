# Customization and extensibility

The framework is designed so that most components can be replaced or extended for your use case. This page summarizes what is configurable and how to plug in custom behavior.

## Runtime

- **Transport**: Use any implementation of the Transport interface (`start`, `stop`, `send(message)`, `receive()`). Built-in: Local, TCP, WebSocket (optional). Pass to `AgentRuntime(transport=...)`.
- **Inbox**: Default `Inbox` supports `maxsize` and `drop_when_full`. To customize: pass `inbox=your_inbox` to `AgentRuntime`. Your object must implement `async push(message)` and `poll(batch_size=10) -> list`. Or pass `inbox_kwargs={"maxsize": 100, "drop_when_full": True}` to configure the default Inbox.
- **Scheduler**: Default event-driven scheduler can be replaced with `scheduler=your_scheduler`. Your object must implement `notify()` and `async wait_for_work(timeout) -> bool`.
- **Executor**: Two options:
  - **executor_factory**: Callable `(agent_id, network, task_manager, pool_manager, **kwargs) -> Executor`. The runtime calls it each run loop to get the executor. Use for a fully custom executor.
  - **executor_kwargs**: Dict of kwargs passed to the default `StandardExecutor` (e.g. `custom_handlers`, `safety_policy`, `bidding_protocols`, `tool_timeout_sec`, `tool_allowlist`). Ignored if `executor_factory` is set.
- **Other runtime options**: `pool_manager`, `task_manager`, `metrics_collector`, `discovery_service`, `agent_descriptor`, `identity_registry`, `replay_log`, `tool_registry`, `checkpoint_store`, `checkpoint_interval_sec`, `health_check`, `ready_check`, `receive_timeout_sec` are all optional and configurable.

## Executor and decisions

- **Custom decision types**: Define a new `Decision` subclass and register an async handler with `StandardExecutor(..., custom_handlers={MyDecision: my_async_handler})`. The handler receives the decision instance; run your logic and return. You can also pass `executor_kwargs={"custom_handlers": {...}}` when constructing the runtime.
- **Safety**: `safety_policy=(ResourceLimits, ActionPolicy)` to restrict decision types and validate task resources.
- **Coordination**: Optional `bidding_protocols`, `negotiation_protocol`, `delegation_protocol`, `votes_store` for built-in decision types.
- **Tools**: `tool_registry` (ToolRegistry) for `InvokeTool`; implement the Tool protocol (`name`, `run(params)`). Optional `tool_timeout_sec` and `tool_allowlist` (set) on StandardExecutor for execution timeout and allowlist. See [Security](../guides/security.md).

## Agent

- **Subclass Agent**: Override `decide(messages, tasks)`, `on_start`, `on_stop`, `on_tick`, `sign_message` as needed. The runtime only requires an object with `id` (and optionally `capabilities`, `topics` for discovery/scoping).

## Policy

- **Admission**: Implement `AdmissionPolicy` (`can_admit(agent_id, context)`) and pass to `create_pool(..., admission_policy=...)` or on the pool spec.
- **Trust**: Implement `TrustModel` (`get_trust`, `update_trust`). Pools can use `trust_model` and `trust_threshold`; `join_pool` checks trust when set.
- **Governance**: Subclass `GovernanceModel` and implement `resolve_dispute(context)`. Pass to `create_pool(..., governance_model=...)` or call when resolving disputes. Built-in: Democratic, Dictatorial, Bicameral, Veto, Empirical.
- **Safety**: Use or extend `ResourceLimits`, `ActionPolicy`, `validate_safety`; pass as `safety_policy` to the executor.

## Storage and discovery

- **Store**: Any implementation of the Store interface (`put`, `get`, `delete`, `list(prefix)`, and optionally **put_if_absent** for atomic put-when-absent). Built-in: MemoryStore (atomic put_if_absent), FileStore (put_if_absent not atomic across processes). Used by PoolManager, TaskManager, DiscoveryService, checkpoint. Stored values must be serializable; schema changes may require migration. See [Store backends](../guides/store_backends.md) for implementing Store with Redis, SQLite, or a database.
- **Discovery**: `DiscoveryService(store=...)`; you can implement custom discovery by providing a different store or wrapping the service. `AgentDescriptor` can carry optional `public_key` for verification.
- **Identity registry**: Implement or use `IdentityRegistry` (fingerprint → public key) for `receive_verified()` on transports.

## Observability

- **Metrics**: Pass `metrics_collector` (e.g. `MetricsCollector`) to the runtime/executor; implement your own collector with `inc`, `gauge`, `snapshot` if needed. `MetricsCollector.format_prometheus()` returns Prometheus text exposition format for scrape endpoints.
- **Replay**: Pass `replay_log` (e.g. `ReplayLog`) to record messages; replace with a custom implementation that implements `record_message(message)` if needed.
- **Tracing**: The runtime uses `trace()` from observability; register a **SpanExporter** via `register_span_exporter(exporter)` so `export(span, duration_sec)` is called when each trace context exits. You can forward to OpenTelemetry or logging.
- **Health/readiness**: Pass `health_check` and `ready_check` callables to the runtime; `is_healthy()` and `is_ready()` delegate to them. No built-in HTTP; poll from a sidecar or CLI.

## Extensions

- **LLM provider**: Implement `chat(messages, **kwargs) -> str`; optionally `chat_stream(...) -> AsyncIterator[str]`. Used by LLMAgent.
- **Tools**: Implement the Tool protocol and register on a `ToolRegistry`.

## Summary table

| Component        | How to customize |
|------------------|------------------|
| Transport        | Implement Transport; pass to runtime |
| Inbox            | Pass `inbox=` or `inbox_kwargs=` to runtime |
| Scheduler        | Pass `scheduler=` to runtime |
| Executor         | Pass `executor_factory=` or `executor_kwargs=` (e.g. custom_handlers) |
| Agent            | Subclass Agent; override decide, lifecycle |
| AdmissionPolicy  | Implement; pass in pool spec |
| TrustModel       | Implement; set on pool |
| GovernanceModel  | Subclass; pass governance_model in pool spec |
| Store            | Implement Store; pass to managers/discovery |
| MetricsCollector | Implement; pass to runtime/executor |
| ReplayLog        | Implement record_message; pass to runtime |
| Tool             | Implement Tool protocol; register on ToolRegistry |
| LLM provider     | Implement chat (and optionally chat_stream) |

For API details, see the [API reference](../api/index.md) and the docstrings of the classes above.
