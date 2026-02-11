# converge

**A distributed operating system for agents.**

Converge provides the foundational substrate for multi-agent computation: identity, messaging, discovery, coordination, and execution so that networks of autonomous agents can operate without central control. The library is agent-first, network-native, and task-oriented; it exposes primitives and pluggable transports, policy, and observability rather than a single prescribed workflow.

```{toctree}
:maxdepth: 2
:caption: Documentation

user_guide/index
api/index
architecture/index
```

## Features

- **Agent-first:** Identity, capabilities, and execution loop are first-class; agents are the only actors.
- **Network-native:** Agents are peers; no central controller is required.
- **Task-oriented:** Discovery, execution, coordination, and evaluation are explicit and inspectable.
- **Observable:** Message flows, task state, and decision points can be logged, traced, and replayed.
- **Transport-agnostic:** Local in-process, TCP, or pluggable transports via a common interface.
- **Pluggable persistence:** In-memory or file-backed stores for pools, tasks, and discovery; crypto and LLM extensions optional.

## Documentation map

| Section | Contents |
|--------|----------|
| **User guide** | Installation, quick start, core concepts, extensions, CLI and configuration. |
| **API reference** | Full API for all public modules (core, network, coordination, runtime, policy, observability, extensions). |
| **Architecture** | Design principles, module layout, process model, failure handling. |

## Quick links

- [Installation](user_guide/installation.md)
- [Quick start](user_guide/quickstart.md)
- [Concepts](user_guide/concepts.md): agents, identity, messages, topics, tasks, pools, decisions
- [Extensions](user_guide/extensions.md): crypto, LLM, storage
- [CLI and configuration](user_guide/cli_and_config.md)
- [API reference](api/index.md): [Project reference](api/project_reference.md) (module index)
- [Architecture](architecture/index.md)
- [Scaling and deployment](guides/scaling.md)
- [Glossary](glossary.md)

## Requirements and status

- **Python:** 3.11 or newer.
- **Status:** Experimental; APIs may change. Use at your own risk.

## License and contributing

See the project repository for license and contribution guidelines.
