# converge.observability

Logging, tracing, metrics, and replay. **Logging**: JsonFormatter for structured logs, configure_logging, get_logger, log_struct. **Tracing**: trace context manager and get_current_trace_id for span tracking; optional **SpanExporter** (register via register_span_exporter) is invoked when a trace() context exits with (span, duration_sec). **MetricsCollector**: counters and gauges with snapshot(); **format_prometheus()** returns Prometheus text exposition format for scrape endpoints. **ReplayLog** records directional message events (`record_inbound`, `record_outbound`; `record_message` compatibility alias), and **ReplayRunner** replays filtered events into inbox/callback targets in deterministic timestamp order. **CoordinationMetrics** provides stable task/pool metric helpers.

**Operations:** **AgentRuntime** supports optional **health_check** and **ready_check** callables (`is_healthy()`, `is_ready()`), and `RuntimeOpsServer` exposes `/health`, `/ready`, and `/metrics` over stdlib HTTP.

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

.. automodule:: converge.observability.coordination_metrics
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.observability.runtime_ops
   :members:
   :undoc-members:
   :show-inheritance:
```
