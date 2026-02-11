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

There is no built-in rate limiting or quotas in the core. Recommend applying them at the gateway or transport layer (e.g. reverse proxy, custom Transport wrapper) or in a sidecar that fronts the agent process.

## Hooks and middleware

Pre-send and post-receive hooks are not a dedicated API. You can implement them as a custom Transport wrapper (decorate or wrap the transport and add checks before/after send/receive) or in `Agent.on_tick` / decision handling. No core API change is required.
