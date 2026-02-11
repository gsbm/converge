# Core concepts

Converge models a **distributed operating system for agents**. The main abstractions are: agent, identity, message, topic, task, pool, store, and decisions. The runtime executes an agent’s decisions via an executor; discovery, coordination, and policy plug into this model.

## Agent

An **agent** is an autonomous computational entity with:

- **Identity**: cryptographic, verifiable (see [Identity](#identity)).
- **State**: e.g. idle, busy, offline; the library does not impose a fixed state machine.
- **Capabilities**: skills and constraints it declares for discovery.
- **Execution loop**: the runtime polls messages and tasks, calls `decide(messages, tasks)`, and executes the returned decisions.

Agents may be rule-based, LLM-driven (see [Extensions](extensions.md)), or hybrid. The core `Agent` class is minimal; subclasses override `decide()` and optionally lifecycle hooks (`on_start`, `on_stop`, `on_tick`).

## Identity

**Identity** is the root of trust:

- Immutable, cryptographically verifiable (Ed25519 in the reference implementation).
- No usernames or human login semantics.
- Used to sign outbound messages and verify authorship.
- Exposes a **fingerprint** (derived from the public key) as the stable agent id.

`Identity.generate()` creates a full keypair; `Identity.from_public_key(public_key)` creates a verify-only identity (no private key). The **identity registry** (`converge.network.identity_registry.IdentityRegistry`) maps fingerprints to public keys so transports can verify message signatures (e.g. `receive_verified()` on compatible transports).

## Message

**Messages** are the primary communication primitive:

- Signed by the sender identity (optional but recommended).
- Carry: sender, optional recipient, topics, payload, timestamp, optional task reference.
- Serialization: `to_bytes()` / `from_bytes()` (msgpack); payload can be encrypted with `encrypt_payload(key)` / `decrypt_payload(key)` (requires 32-byte key; see crypto extension).

Messages support direct (recipient), broadcast (no recipient/topics), or topic-scoped delivery depending on the transport.

## Topic

A **topic** is a semantic namespace used for:

- Routing messages (e.g. transport topic subscriptions).
- Pool formation and scope.
- Discovery (agents advertise topics and capabilities).

Topics are structured (namespace + attributes + optional version), not free-text. They serialize via `to_dict()` / `from_dict()`.

## Task

A **task** is a unit of work with:

- Id, objective, inputs, optional outputs.
- State: PENDING → ASSIGNED → COMPLETED (and optional evaluator).
- Optional assignment and result.
- **Routing** (optional): `pool_id`, `topic`, and `required_capabilities` restrict which agents see the task. When the runtime has a pool manager, it calls `list_pending_tasks_for_agent` so each agent only sees tasks for its pools and capabilities.

Tasks are first-class: submitted to a **task manager**, claimed by agents, and reported via decisions. The task manager can use a **store** for persistence (e.g. in-memory or file-backed).

## Tools and actions

Agents can perform **tool invocations** by emitting an **InvokeTool** decision (`tool_name`, `params`). The runtime’s **StandardExecutor** uses an optional **ToolRegistry** (see `converge.core.tools`): when an InvokeTool is executed, the executor looks up the tool by name and runs `tool.run(params)`. Implement the **Tool** protocol (property `name`, method `run(params) -> Any`) and register tools on a **ToolRegistry**; pass the registry to **AgentRuntime** as `tool_registry` so the executor can run them. Results are not automatically sent back; the agent can emit **ReportTask** or **SendMessage** to report outcomes.

## Pool

A **pool** is a scoped sub-network defined by:

- Topic(s) and optional task types.
- **Admission policy** (who can join: open, whitelist, token, or custom).
- **Governance model** (e.g. democratic, dictatorial) for dispute resolution.
- Set of member agents.

Pools are coordination surfaces. The **pool manager** creates pools, joins/leaves agents, and persists pools via a **store** when provided.

## Store

The **store** abstraction (`converge.core.store.Store`) provides key-value persistence: `put`, `get`, `delete`, `list(prefix)`. Implementations include **MemoryStore** and **FileStore** (see [Extensions](extensions.md)). Pool manager, task manager, and discovery service can use a store for durability.

## Decisions

The agent’s `decide(messages, tasks)` returns a list of **decisions**. The runtime executes them via the **executor** (or a fallback when no pool/task managers are configured). Decision types:

| Type | Purpose |
|------|---------|
| `SendMessage(message=...)` | Send a single message (uses network when executor has one). |
| `JoinPool(pool_id)` | Join a pool (via pool manager). |
| `LeavePool(pool_id)` | Leave a pool. |
| `CreatePool(spec)` | Create a pool from a spec (id, topics, optional admission_policy). |
| `SubmitTask(task=...)` | Submit a task (via task manager). |
| `ClaimTask(task_id)` | Claim a pending task. |
| `ReportTask(task_id, result)` | Report task result and mark completed. |
| `SubmitBid`, `Vote`, `Propose`, `AcceptProposal`, `RejectProposal`, `Delegate`, `RevokeDelegation` | Coordination: bidding, voting, negotiation, delegation (executor uses optional protocols). |

See `converge.core.decisions` in the [API reference](../api/core.md).

## Trust

Trust is non-binary and contextual. The **trust model** (`converge.policy.trust`) maintains per-agent scores, updatable from outcomes; discovery queries can use a trust threshold. Trust is computed from history where applicable, not only declared.

## Message verification and identity bootstrapping

When an **IdentityRegistry** is passed to **AgentRuntime**, the runtime uses **receive_verified()** and only pushes messages that verify against the sender’s public key; unverified messages are dropped (log at debug). Populate the registry from discovery: include **public_key** in **AgentDescriptor** when registering (e.g. via **build_descriptor**, which adds the agent’s identity public key), then after querying, call **identity_registry.register(d.id, d.public_key)** for each descriptor so received messages can be verified.

## Discovery and registration

The **discovery service** holds **agent descriptors** (id, topics, capabilities, optional public_key). It can load/save descriptors from a **store** and answers **queries** (by topics and/or capabilities) over a candidate list. Agents **register on runtime start** and **unregister on stop**: when you pass `discovery_service` (and optionally `agent_descriptor`) to `AgentRuntime`, the runtime registers the agent at start so peers can find it by topic/capability, and unregisters it at stop. Use `build_descriptor(agent)` from `converge.network.network` to build a descriptor from an agent’s id, topics, and capabilities when you do not provide one. The **network** (`AgentNetwork`) wraps a transport and local agent set and exposes `discover(query)` using descriptors registered with it.

## Governance and safety

- **Pools** enforce local rules (admission, governance model, optional trust threshold). When a pool has **trust_model** and **trust_threshold**, join is allowed only if the agent’s trust score is at least the threshold.
- **Policy enforcement in the executor:** When **StandardExecutor** is given a **safety_policy** (ResourceLimits, ActionPolicy), it checks ActionPolicy before each decision (only allowed types run) and validates task resource constraints (cpu, memory_mb) for SubmitTask/ClaimTask.
- **Policy** modules provide admission (open, whitelist, token), trust, governance (e.g. democratic, dictatorial), and safety (resource limits, action allowlists). See [Architecture/Process model](../architecture/process_model.md) and [API/policy](../api/policy.md).

## Recovery

**Pool and task state** are persisted in the **Store** used by PoolManager and TaskManager. On restart, create PoolManager and TaskManager with the **same store** (e.g. FileStore with the same path) so pools and tasks are restored. The **inbox** is not persisted; message replay is best-effort unless the transport supports it. The runtime’s optional **checkpoint_store** and **checkpoint_interval_sec** write a lightweight checkpoint (e.g. agent_id → last_activity_ts) for observability; they do not change processing or replay semantics.

For the full API and process model, see [Architecture](../architecture/index.md) and the [API reference](../api/index.md).
