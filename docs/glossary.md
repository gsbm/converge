# Glossary

| Term | Definition |
|------|-------------|
| **Agent** | Autonomous computational entity with identity, capabilities, and an execution loop that produces decisions. See [Concepts](user_guide/concepts.md#agent). |
| **Identity** | Cryptographic (e.g. Ed25519) keypair; fingerprint is the stable agent id. Used to sign and verify messages. See [Concepts](user_guide/concepts.md#identity). |
| **Message** | Communication primitive: sender, optional recipient, topics, payload, optional signature. See [Concepts](user_guide/concepts.md#message). |
| **Topic** | Semantic namespace for routing, pool scope, and discovery. See [Concepts](user_guide/concepts.md#topic). |
| **Task** | Unit of work with objective, constraints, and lifecycle (pending → assigned → completed/failed/cancelled). See [Concepts](user_guide/concepts.md#task). |
| **Pool** | Scoped sub-network with membership, admission, and optional governance. See [Concepts](user_guide/concepts.md#pool). |
| **Decision** | Action emitted by an agent (e.g. SendMessage, ClaimTask, ReportTask). Executor runs them. See [API/core](api/core.md). |
| **Executor** | Runs decisions (e.g. StandardExecutor). See [API/runtime](api/runtime.md). |
| **Discovery** | Service and queries to find agents by topic/capability. See [Concepts](user_guide/concepts.md#discovery-and-registration). |
| **Governance** | Model for resolving disputes in a pool (e.g. democratic, dictatorial). See [Concepts](user_guide/concepts.md#governance-and-safety). |
| **Admission** | Policy that controls who can join a pool (open, whitelist, token). See [API/policy](api/policy.md). |
| **Trust** | Per-agent scores used for discovery threshold and context. See [Concepts](user_guide/concepts.md#trust). |
| **Transport** | Layer for sending and receiving messages (local, TCP, WebSocket). See [Design](architecture/design.md#transport-layer). |
| **Store** | Key-value persistence for pools, tasks, discovery. See [Store backends](guides/store_backends.md). |
| **Capability** | Declared skill or constraint of an agent for discovery. See [Concepts](user_guide/concepts.md#agent). |
