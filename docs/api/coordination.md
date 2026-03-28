# converge.coordination

Pool and task management, negotiation, consensus, bidding, and delegation. **PoolManager** and **TaskManager** create/join/leave pools and submit/claim/report tasks; both can use a store for persistence. **TaskManager** also supports **cancel_task(task_id)** (move to CANCELLED), **fail_task(task_id, reason, agent_id=...)** (move to FAILED), and **release_expired_claims(now_ts)** to return tasks to PENDING when claim_ttl_sec has elapsed (call periodically with time.monotonic()). **PoolManager.get_pools_for_agent(agent_id)** returns the list of pool IDs the agent has joined. **TaskManager.list_pending_tasks_for_agent(agent_id, pool_ids, capabilities, topics=..., sort_by_priority=..., refresh_from_store=...)** returns pending tasks visible to that agent (filtered by pool membership, capabilities, and optionally topic; optional sort by **task.priority** descending). Use `refresh_from_store=True` in shared-store/multi-process deployments for an eager refresh; default is eventual consistency. Tasks can set **priority** (int, default 0) and **topic** (Topic) for routing; the runtime passes agent topics from **agent_descriptor** when set. **NegotiationProtocol** manages sessions (propose, counter, accept, reject). **Consensus** provides majority and plurality voting. **BiddingProtocol** and **DelegationProtocol** support resource allocation and delegation of scope. The **StandardExecutor** can run coordination decisions when given optional **bidding_protocols** (auction_id → BiddingProtocol), **negotiation_protocol**, **delegation_protocol**, and **votes_store** (for Vote). See [Customization — Protocol lifecycle](../user_guide/customization.md#protocol-lifecycle-and-wiring) for when and how to wire these into the executor. Decision types: **SubmitBid**, **Vote**, **Propose**, **AcceptProposal**, **RejectProposal**, **Delegate**, **RevokeDelegation** (see [Core decisions](core.md)).

```{eval-rst}
.. automodule:: converge.coordination.pool_manager
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.coordination.task_manager
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.coordination.negotiation
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.coordination.consensus
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.coordination.bidding
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.coordination.delegation
   :members:
   :undoc-members:
   :show-inheritance:
```
