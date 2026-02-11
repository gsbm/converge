# converge.core

Core abstractions: agent, identity, message, topic, task, pool, capability, store, and decisions. These types are used everywhere: identity and messages for communication, topics for routing and discovery, tasks and pools for coordination, capabilities for discovery, store for persistence, and decisions as the output of the agent’s `decide()` and input to the executor.

**Task routing:** Tasks can optionally set `pool_id`, `topic`, and `required_capabilities`. Only agents in the given pool and with the required capabilities see the task when the runtime uses scoped task listing (see coordination and runtime).

**Task constraints:** Conventional keys in `task.constraints` (enforced by custom logic if needed): `timeout_sec`, `deadline`, `claim_ttl_sec`, `max_retries`, `cpu`, `memory_mb`. See Task docstring and coordination docs for cancel, fail, and claim TTL.

**Tools and actions:** Agents can emit an **InvokeTool** decision (`tool_name`, `params`). The runtime’s executor looks up the tool in an optional **ToolRegistry** (see `converge.core.tools`) and runs it; implement the **Tool** protocol (`name`, `run(params)`).

```{eval-rst}
.. automodule:: converge.core.agent
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.core.identity
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.core.message
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.core.topic
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.core.task
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.core.pool
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.core.capability
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.core.store
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.core.decisions
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.core.tools
   :members:
   :undoc-members:
   :show-inheritance:
```
