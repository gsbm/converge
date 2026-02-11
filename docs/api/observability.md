# converge.observability

Logging, tracing, metrics, and replay. **Logging**: JsonFormatter for structured logs, configure_logging, get_logger, log_struct. **Tracing**: trace context manager and get_current_trace_id for span tracking. **MetricsCollector**: counters and gauges with snapshot(). **ReplayLog**: record messages and export/load event logs for replay and inspection. When passed to **AgentRuntime** as `replay_log`, the runtime records every incoming message (in the listen loop) and the executor records every outgoing **SendMessage**; this enables audit trails and replay.

```{eval-rst}
.. automodule:: converge.observability.logging
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.observability.tracing
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.observability.metrics
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.observability.replay
   :members:
   :undoc-members:
   :show-inheritance:
```
