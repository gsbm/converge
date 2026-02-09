# API reference

The API is organized by package. Each page includes a short overview and auto-generated documentation from the source. Use the [project reference](project_reference.md) for a compact index of all public modules and their roles.

```{toctree}
:maxdepth: 2
:caption: Packages

project_reference
core
network
coordination
runtime
policy
observability
extensions
```

## Package summary

| Package | Contents |
|---------|----------|
| **core** | Agent, Identity, Message, Topic, Task, Pool, Capability, Store, Decision types. |
| **network** | AgentNetwork, DiscoveryService, AgentDescriptor, DiscoveryQuery, IdentityRegistry, Transport (base, local, TCP). |
| **coordination** | PoolManager, TaskManager, NegotiationProtocol, Consensus, BiddingProtocol, DelegationProtocol. |
| **runtime** | AgentRuntime, Inbox, Scheduler, Executor protocol, StandardExecutor. |
| **policy** | AdmissionPolicy (Open, Whitelist, Token), TrustModel, Governance (Democratic, Dictatorial), ResourceLimits, ActionPolicy, validate_safety. |
| **observability** | Logging (JsonFormatter, configure_logging, get_logger, log_struct), tracing, MetricsCollector, ReplayLog. |
| **extensions** | MemoryStore, FileStore, crypto (encrypt, decrypt, derive_key, secure_random_bytes), LLMAgent and providers (OpenAI, Anthropic, Mistral). |

Entrypoints:
- **CLI**: `converge.cli.main` (and `converge run` via `converge.cli:main`);
- **programmatic**: construct agents, transports, runtimes, and managers from the API.
