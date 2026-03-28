# Security baseline

Converge provides identity, optional message verification, and tool execution safeguards. Operators should add transport- and deployment-level controls (TLS, rate limiting, quotas) as needed.

## Identity and verification

- **Identity:** Each agent has a cryptographic identity (key pair); the fingerprint identifies the agent. Use `IdentityRegistry` to map fingerprints to public keys.
- **Signing:** Transports that support verification can sign outgoing messages and verify incoming ones.
- **Receive verified:** When the runtime is configured with `identity_registry`, it uses `receive_verified()` and drops or rejects messages that fail verification (logged at debug). Populate the registry from discovery or a store to enable verified receive.

## Tool execution safety

- **Tool allowlist:** Pass `tool_allowlist` (a set of allowed tool names) via `executor_kwargs` to the runtime. The executor skips any InvokeTool whose tool name is not in the set and logs a warning.
- **Tool timeout:** Pass `tool_timeout_sec` via `executor_kwargs` to limit how long each tool run may take. On timeout the call is cancelled and an error is logged; the agent can report task failure separately.

See the [runtime API](api/runtime.md) and [customization](user_guide/customization.md) for wiring `executor_kwargs` (e.g. `tool_timeout_sec`, `tool_allowlist`).

## Rate limiting and quotas

Converge provides first-class token-bucket rate limiting via:

- `RateLimiter` (global/sender/topic buckets),
- `RateLimitHook` for transport middleware enforcement,
- optional egress enforcement in `StandardExecutor` when `rate_limiter` is set.

Recommended baseline:

1. enforce ingress limits with `HookedTransport(..., hooks=[RateLimitHook(...)])`,
2. enforce egress limits by passing `rate_limiter` to executor wiring,
3. monitor dropped counters (`rate_limit_ingress_dropped_total`, `rate_limit_egress_dropped_total`).

## Hooks and middleware

Use `HookedTransport` + `MessageHook` for reusable middleware:

- `pre_send(message) -> message | None`,
- `post_receive(message) -> message | None`,
- optional `on_error(stage, error, context)`.

Execution order is deterministic (registration order). Returning `None` drops a message.

For runtime paths not covered by transport wrapping, use runtime hooks (`runtime_hooks=`):

- `on_fallback_pre_send(message)`,
- `on_unverified_drop(context)`.
