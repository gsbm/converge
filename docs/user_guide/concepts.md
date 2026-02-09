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

Tasks are first-class: submitted to a **task manager**, claimed by agents, and reported via decisions. The task manager can use a **store** for persistence (e.g. in-memory or file-backed).

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

See `converge.core.decisions` in the [API reference](../api/core.md).

## Trust

Trust is non-binary and contextual. The **trust model** (`converge.policy.trust`) maintains per-agent scores, updatable from outcomes; discovery queries can use a trust threshold. Trust is computed from history where applicable, not only declared.

## Discovery

The **discovery service** holds **agent descriptors** (id, topics, capabilities). It can load/save descriptors from a **store** and answers **queries** (by topics and/or capabilities) over a candidate list. The **network** (`AgentNetwork`) wraps a transport and local agent set and exposes `discover(query)` using descriptors registered with it.

## Governance and safety

- **Pools** enforce local rules (admission, governance model).
- **Policy** modules provide admission (open, whitelist, token), trust, governance (e.g. democratic, dictatorial), and safety (resource limits, action allowlists). See [Architecture/Process model](../architecture/process_model.md) and [API/policy](../api/policy.md).

For the full API and process model, see [Architecture](../architecture/index.md) and the [API reference](../api/index.md).
