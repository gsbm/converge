from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

from converge.core.store import Store
from converge.extensions.storage.memory import MemoryStore


class WebhookSecurityError(ValueError):
    pass


@dataclass(frozen=True)
class ProviderProfile:
    name: str
    secret_ref: str
    signature_header: str = "X-Webhook-Signature"
    timestamp_header: str = "X-Webhook-Timestamp"
    event_id_field: str = "event_id"
    signature_algorithm: str = "sha256"
    canonicalization: str = "raw_body"
    required_payload_fields: tuple[str, ...] = ()
    subject_field: str = "subject"
    source_field: str = "source"
    emit_as: str = "message"  # message|task


@dataclass(frozen=True)
class WebhookSecurityPolicy:
    timestamp_skew_limit_sec: int = 300
    idempotency_ttl_sec: int = 3600
    max_payload_bytes: int = 1024 * 1024
    allowed_content_types: tuple[str, ...] = ("application/json",)
    require_mtls: bool = False
    ip_allowlist: tuple[str, ...] = ()
    strict_mode: bool = True


class WebhookSecurity:
    def __init__(
        self,
        policy: WebhookSecurityPolicy,
        provider_profiles: dict[str, ProviderProfile],
        secrets: dict[str, str],
        *,
        store: Store | None = None,
    ) -> None:
        self.policy = policy
        self.provider_profiles = provider_profiles
        self.secrets = secrets
        self.store = store or MemoryStore()

    def _normalize_headers(self, headers: dict[str, str]) -> dict[str, str]:
        return {k.lower(): v for k, v in headers.items()}

    def _get_secret(self, profile: ProviderProfile) -> str:
        secret = self.secrets.get(profile.secret_ref)
        if not secret:
            raise WebhookSecurityError("provider secret not configured")
        return secret

    def _canonical_bytes(self, profile: ProviderProfile, raw_body: bytes, payload: dict[str, Any]) -> bytes:
        if profile.canonicalization == "raw_body":
            return raw_body
        if profile.canonicalization == "json_sorted":
            return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        raise WebhookSecurityError(f"unsupported canonicalization: {profile.canonicalization}")

    def _validate_payload_shape(self, profile: ProviderProfile, payload: dict[str, Any]) -> None:
        for required_name in profile.required_payload_fields:
            if required_name not in payload:
                raise WebhookSecurityError(f"missing required payload field: {required_name}")

    def _dedupe_key(self, provider: str, event_id: str) -> str:
        return f"webhook:dedupe:{provider}:{event_id}"

    def _cleanup_expired_dedupe(self, now_ts: float) -> None:
        ttl = float(self.policy.idempotency_ttl_sec)
        for key in self.store.list("webhook:dedupe:"):
            record = self.store.get(key)
            if not isinstance(record, dict):
                self.store.delete(key)
                continue
            seen_at = float(record.get("seen_at", 0))
            if now_ts - seen_at > ttl:
                self.store.delete(key)

    def validate_and_extract(
        self,
        provider: str,
        *,
        method: str,
        headers: dict[str, str],
        raw_body: bytes,
        remote_addr: str | None = None,
        client_cert_present: bool = False,
    ) -> tuple[ProviderProfile, dict[str, Any], str, float]:
        if method.upper() != "POST":
            raise WebhookSecurityError("only POST is allowed")
        if provider not in self.provider_profiles:
            raise WebhookSecurityError("unknown provider")
        profile = self.provider_profiles[provider]

        if self.policy.ip_allowlist and (remote_addr or "") not in self.policy.ip_allowlist:
            raise WebhookSecurityError("remote IP not allowlisted")
        if self.policy.require_mtls and not client_cert_present:
            raise WebhookSecurityError("mTLS client certificate required")
        if len(raw_body) > self.policy.max_payload_bytes:
            raise WebhookSecurityError("payload too large")

        normalized = self._normalize_headers(headers)
        content_type = normalized.get("content-type", "")
        if not any(content_type.startswith(t) for t in self.policy.allowed_content_types):
            raise WebhookSecurityError("content type not allowed")

        sig_name = profile.signature_header.lower()
        ts_name = profile.timestamp_header.lower()
        signature = normalized.get(sig_name)
        ts_str = normalized.get(ts_name)
        if not signature or not ts_str:
            raise WebhookSecurityError("missing signature headers")
        try:
            ts = float(ts_str)
        except ValueError as e:
            raise WebhookSecurityError("invalid timestamp header") from e

        now_ts = time.time()
        if abs(now_ts - ts) > float(self.policy.timestamp_skew_limit_sec):
            raise WebhookSecurityError("timestamp outside allowed skew window")

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            raise WebhookSecurityError("invalid JSON payload") from e
        if not isinstance(payload, dict):
            raise WebhookSecurityError("payload must be a JSON object")
        self._validate_payload_shape(profile, payload)

        secret = self._get_secret(profile)
        canonical = self._canonical_bytes(profile, raw_body, payload)
        digest = hmac.new(secret.encode("utf-8"), canonical, getattr(hashlib, profile.signature_algorithm))
        expected = digest.hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise WebhookSecurityError("signature mismatch")

        event_id_raw = payload.get(profile.event_id_field) or normalized.get("x-webhook-event-id")
        if not isinstance(event_id_raw, str) or not event_id_raw:
            raise WebhookSecurityError("missing or invalid event id")
        event_id = event_id_raw

        self._cleanup_expired_dedupe(now_ts)
        dedupe_key = self._dedupe_key(provider, event_id)
        existing = self.store.get(dedupe_key)
        if existing is not None:
            raise WebhookSecurityError("duplicate event id")
        self.store.put(dedupe_key, {"seen_at": now_ts})
        return profile, payload, event_id, ts
