# Webhook connector sidecar

Converge includes a generic webhook connector extension for production-grade ingress/egress bridging.

## Architecture

- **Sidecar HTTP service** handles inbound webhook requests and outbound webhook dispatch.
- **WebhookConnector** enforces strict security, dedupe, and retry/circuit-breaker policies.
- **Bridge topics**:
  - `bridge.webhook.inbound`: normalized inbound event translated to `Message` or `Task`.
  - `bridge.webhook.outbound`: outbound routing instructions translated to HTTP actions.

## Security checklist (strict baseline)

- Require HMAC signature verification with provider-specific profile.
- Require timestamp skew checks (`timestamp_skew_limit_sec`).
- Require inbound idempotency (`provider + event_id`) with TTL.
- Enforce content-type allowlist and payload size limits.
- Deny unknown providers by default.
- Optional hardening:
  - IP allowlist
  - mTLS requirement hook

## Provider profile example

```toml
bind = "0.0.0.0"
port = 8090

[[providers]]
name = "acme"
secret_ref = "acme_webhook_secret"
signature_header = "X-Webhook-Signature"
timestamp_header = "X-Webhook-Timestamp"
event_id_field = "event_id"
canonicalization = "raw_body"
required_payload_fields = ["event_id", "subject"]
emit_as = "message"

[secrets]
acme_webhook_secret = "replace-me"
```

Run:

```bash
converge webhook-sidecar --config sidecar.toml --json-logs
```

## Endpoints

- `POST /webhook/<provider>`: validated inbound event ingestion.
- `POST /outbound`: queue outbound action payload.
- `GET /healthz`: liveness.
- `GET /readyz`: readiness.
- `GET /metrics`: Prometheus text metrics.

## Runbooks

### Secret rotation

1. Introduce new secret value in config/secrets manager.
2. Roll sidecar instances with new secret.
3. Keep overlap window for senders still signing with old secret.
4. Remove old secret and verify no signature mismatch spikes.

### Replay attack response

1. Alert on `webhook_inbound_rejected_total` growth with duplicate/timestamp errors.
2. Tighten timestamp skew window temporarily if abuse is active.
3. Rotate affected provider secret and invalidate sender credentials.

### Dead-letter draining

1. Inspect dead-letter store keys (`webhook:dead_letter:*`).
2. Identify root cause (upstream outage, schema error, auth failure).
3. Replay actions after mitigation or archive permanently with incident record.

### Outbound incident triage

1. Check circuit-breaker open counters.
2. Validate upstream status and DNS/TLS reachability.
3. Tune retry policy only after understanding downstream SLO impact.
