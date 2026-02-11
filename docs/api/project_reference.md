# Project reference

Compact index of public modules and their role. For full signatures and docstrings, use the linked API pages.

## converge

| Module | Role |
|--------|------|
| `converge.cli` | CLI entrypoint: argument parsing, config loading (env + YAML/TOML), `converge run` loop. |
| `converge.__main__` | Calls `cli.main()` when run as `python -m converge`. |

## converge.core

| Module | Role |
|--------|------|
| `converge.core.agent` | Agent base class: identity, `decide()`, `sign_message()`, lifecycle hooks. |
| `converge.core.identity` | Ed25519 identity: generate, from_public_key, fingerprint, sign/verify. |
| `converge.core.message` | Message: sender, recipient, topics, payload; sign, verify, to_bytes/from_bytes, encrypt_payload/decrypt_payload. |
| `converge.core.topic` | Topic: namespace, attributes, version; to_dict/from_dict. |
| `converge.core.task` | Task: id, objective, inputs, state, assigned_to, result. |
| `converge.core.pool` | Pool: id, topics, agents, add_agent/remove_agent. |
| `converge.core.capability` | Capability and CapabilitySet: name, version, description, constraints, costs. |
| `converge.core.store` | Store ABC: put, get, delete, list. |
| `converge.core.decisions` | Decision types: SendMessage, JoinPool, LeavePool, CreatePool, SubmitTask, ClaimTask, ReportTask, SubmitBid, Vote, Propose, AcceptProposal, RejectProposal, Delegate, RevokeDelegation, InvokeTool. |
| `converge.core.tools` | Tool protocol, ToolRegistry: register, get, list_names; for InvokeTool execution. |

## converge.network

| Module | Role |
|--------|------|
| `converge.network.network` | AgentNetwork: wraps transport; register_agent, unregister_agent, send, broadcast, discover. |
| `converge.network.discovery` | AgentDescriptor, DiscoveryQuery, DiscoveryService: register, unregister, query; optional store persistence. |
| `converge.network.identity_registry` | IdentityRegistry: map agent_id → public_key for verification. |
| `converge.network.transport.base` | Transport ABC: start, stop, send, receive. |
| `converge.network.transport.local` | LocalTransport, LocalTransportRegistry: in-process, topic subscriptions, recipient/topic routing. |
| `converge.network.transport.tcp` | TcpTransport: length-prefixed msgpack, topic-based routing, connection pool. |
| `converge.network.transport.websocket` | WebSocket transport (optional; requires `converge[websocket]`). |

## converge.coordination

| Module | Role |
|--------|------|
| `converge.coordination.pool_manager` | PoolManager: create_pool, join_pool, leave_pool, get_pool; optional store. |
| `converge.coordination.task_manager` | TaskManager: submit, claim, report, get_task, list_pending_tasks; optional store. |
| `converge.coordination.negotiation` | NegotiationProtocol: create_session, propose, accept, reject; NegotiationState. |
| `converge.coordination.consensus` | Consensus: majority_vote, plurality_vote. |
| `converge.coordination.bidding` | BiddingProtocol: submit_bid, resolve. |
| `converge.coordination.delegation` | DelegationProtocol: delegate, revoke. |

## converge.runtime

| Module | Role |
|--------|------|
| `converge.runtime.loop` | AgentRuntime, Inbox: start/stop, discovery/identity_registry/replay_log/checkpoint_store/tool_registry. |
| `converge.runtime.scheduler` | Scheduler: notify, wait_for_work(timeout). |
| `converge.runtime.executor` | Executor protocol, StandardExecutor: execute decisions including SendMessage, SubmitTask, ClaimTask, JoinPool, LeavePool, CreatePool, ReportTask, coordination (SubmitBid, Vote, Propose, etc.), InvokeTool; optional tool_registry, replay_log, safety_policy. |

## converge.policy

| Module | Role |
|--------|------|
| `converge.policy.admission` | AdmissionPolicy ABC; OpenAdmission, WhitelistAdmission, TokenAdmission. |
| `converge.policy.trust` | TrustModel: get_trust, update_trust. |
| `converge.policy.governance` | GovernanceModel ABC; DemocraticGovernance, DictatorialGovernance. |
| `converge.policy.safety` | ResourceLimits, ActionPolicy, validate_safety. |

## converge.observability

| Module | Role |
|--------|------|
| `converge.observability.logging` | JsonFormatter, configure_logging, get_logger, log_struct. |
| `converge.observability.tracing` | trace context manager, get_current_trace_id. |
| `converge.observability.metrics` | MetricsCollector: inc, gauge, snapshot. |
| `converge.observability.replay` | ReplayLog: record_message, export, load. |

## converge.extensions

| Module | Role |
|--------|------|
| `converge.extensions.storage.memory` | MemoryStore: in-memory Store implementation. |
| `converge.extensions.storage.file` | FileStore: file-backed Store (pickle, one file per key). |
| `converge.extensions.crypto` | encrypt, decrypt, derive_key, secure_random_bytes. |
| `converge.extensions.llm` | LLMAgent, OpenAIProvider, AnthropicProvider, MistralProvider; base provider interface. |
