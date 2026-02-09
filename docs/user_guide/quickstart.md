# Quick start

This section gives a minimal runnable example: two agents with cryptographic identities, local transports, and runtimes; one sends a message, the other receives it.

## Prerequisites

- Python 3.11+
- `pip install converge` (or `pip install -e .` from source).

## Example: two agents, local transport

```python
import asyncio
from converge.core.identity import Identity
from converge.core.agent import Agent
from converge.core.message import Message
from converge.network.transport.local import LocalTransport
from converge.runtime.loop import AgentRuntime

async def main():
    # 1. Identities (Ed25519 keypairs; fingerprint = agent id)
    id_a = Identity.generate()
    id_b = Identity.generate()

    # 2. Agents (default decide() returns no decisions)
    agent_a = Agent(id_a)
    agent_b = Agent(id_b)

    # 3. Transports (share a process-local registry)
    transport_a = LocalTransport(id_a.fingerprint)
    transport_b = LocalTransport(id_b.fingerprint)

    # 4. Runtimes
    runtime_a = AgentRuntime(agent_a, transport_a)
    runtime_b = AgentRuntime(agent_b, transport_b)
    await runtime_a.start()
    await runtime_b.start()

    # 5. Send a signed message from A to B (B's inbox receives it)
    msg = Message(sender=id_a.fingerprint, recipient=id_b.fingerprint, payload={"text": "hello"})
    signed = msg.sign(id_a)
    await transport_a.send(signed)

    # 6. B receives (e.g. in its loop); here we read once for illustration
    received = await transport_b.receive()
    assert received.payload["text"] == "hello"

    await runtime_a.stop()
    await runtime_b.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## What this uses

- **Identity:** Ed25519 keypair and fingerprint; used to sign messages and identify agents.
- **Agent:** Holds identity; `decide(messages, tasks)` returns a list of decisions (here the default agent returns none).
- **Message:** Sender, optional recipient, payload; can be signed and verified.
- **LocalTransport:** In-process transport; agents register with a singleton registry and deliver by recipient or topic.
- **AgentRuntime:** Wraps an agent and a transport; runs the execution loop (poll inbox/tasks → decide → execute decisions) and starts/stops the transport.

## Next steps

- [Concepts](concepts.md): agents, pools, tasks, topics, decisions.
- [CLI and configuration](cli_and_config.md): run an agent with `converge run`.
- [Extensions](extensions.md): crypto, LLM agents, storage backends.
- [API reference](../api/index.md): full API for all modules.
