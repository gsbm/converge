# converge.network

Network facade, discovery service, identity registry, and transport layer. **AgentNetwork** wraps a transport and local agent set and exposes send, broadcast, and discover. **build_descriptor(agent)** builds an `AgentDescriptor` from an agent (id, topics, capabilities) for use with discovery. **DiscoveryService** holds agent descriptors and answers queries by topics and capabilities; it can persist descriptors via a store. When `AgentRuntime` is constructed with `discovery_service` (and optionally `agent_descriptor`), the runtime registers the agent on start and unregisters it on stop so peers can discover it. **IdentityRegistry** maps agent ids to public keys for signature verification. **Transports** (base, local, TCP, optional WebSocket) implement start/stop, send, and receive; local transport supports topic subscriptions and recipient-based delivery. When **AgentRuntime** is given an **identity_registry**, it uses **receive_verified()** and drops messages that fail verification (log at debug). Populate the registry from discovery (descriptors with **public_key**) or from store to enable verified receive.

```{eval-rst}
.. automodule:: converge.network.network
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.network.identity_registry
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.network.discovery
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.network.transport.base
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.network.transport.local
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.network.transport.tcp
   :members:
   :undoc-members:
   :show-inheritance:
```
