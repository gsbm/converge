# Architecture

Design principles, module layout, and process model for converge.

```{toctree}
:maxdepth: 2
:caption: Architecture

design
process_model
```

## Overview

Converge is structured as a small core (identity, agent, message, topic, task, pool, capability, store, decisions), a network layer (discovery, identity registry, transports), coordination (pool and task managers, negotiation, consensus, bidding, delegation), a runtime (loop, scheduler, executor), policy (admission, trust, governance, safety), and observability (logging, tracing, metrics, replay). Optional extensions add storage backends, crypto, and LLM-driven agents. The [design](design.md) document describes the module layout and runtime model; the [process model](process_model.md) describes task flow, governance, and failure handling.
