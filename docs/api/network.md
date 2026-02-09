# converge.network

Network facade, discovery service, identity registry, and transport layer. **AgentNetwork** wraps a transport and local agent set and exposes send, broadcast, and discover. **DiscoveryService** holds agent descriptors and answers queries by topics and capabilities; it can persist descriptors via a store. **IdentityRegistry** maps agent ids to public keys for signature verification. **Transports** (base, local, TCP, optional WebSocket) implement start/stop, send, and receive; local transport supports topic subscriptions and recipient-based delivery.

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
