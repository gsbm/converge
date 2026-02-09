# converge.coordination

Pool and task management, negotiation, consensus, bidding, and delegation. **PoolManager** and **TaskManager** create/join/leave pools and submit/claim/report tasks; both can use a store for persistence. **NegotiationProtocol** manages sessions (propose, counter, accept, reject). **Consensus** provides majority and plurality voting. **BiddingProtocol** and **DelegationProtocol** support resource allocation and delegation of scope.

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
