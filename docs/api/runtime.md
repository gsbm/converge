# converge.runtime

Execution loop, scheduler, and executor. **AgentRuntime** runs the agent loop: wait for work, poll inbox and task manager, call agent.decide(), execute decisions via **StandardExecutor** (or fallback when no managers are set). Optional **claim_ttl_interval_sec** enables automatic release of expired task claims; optional **task_poll_interval_sec** runs a periodic task poll that notifies the scheduler when pending tasks change so the loop wakes sooner. **Inbox** buffers messages (bounded, optional drop-when-full). **Scheduler** provides event-driven wake-up with timeout. **StandardExecutor** handles SendMessage, SubmitTask, ClaimTask, JoinPool, LeavePool, CreatePool, ReportTask; it uses the network and managers injected at construction.

```{eval-rst}
.. automodule:: converge.runtime.loop
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.runtime.scheduler
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.runtime.executor
   :members:
   :undoc-members:
   :show-inheritance:
```
