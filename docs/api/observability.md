# converge.observability

Logging, tracing, metrics, and replay. **Logging**: JsonFormatter for structured logs, configure_logging, get_logger, log_struct. **Tracing**: trace context manager and get_current_trace_id for span tracking; optional **SpanExporter** (register via register_span_exporter) is invoked when a trace() context exits with (span, duration_sec). **MetricsCollector**: counters and gauges with snapshot(); **format_prometheus()** returns Prometheus text exposition format for scrape endpoints. Expose it from an HTTP server in your code (e.g. `/metrics`). **ReplayLog**: record messages and export/load event logs for replay and inspection. When passed to **AgentRuntime** as `replay_log`, the runtime records every incoming message (in the listen loop) and the executor records every outgoing **SendMessage**; this enables audit trails and replay.

**Operations:** **AgentRuntime** supports optional **health_check** and **ready_check** callables; **is_healthy()** and **is_ready()** delegate to them (default True when unset). There is no built-in HTTP server; operators can poll these from a sidecar or CLI.

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
