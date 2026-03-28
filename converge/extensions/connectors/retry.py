from __future__ import annotations

import random
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class WebhookRetryPolicy:
    max_attempts: int = 5
    base_delay_sec: float = 0.25
    max_delay_sec: float = 10.0
    jitter_ratio: float = 0.2
    request_timeout_sec: float = 5.0

    def compute_delay(self, attempt: int) -> float:
        exp_delay = min(self.max_delay_sec, self.base_delay_sec * (2 ** max(0, attempt - 1)))
        jitter = exp_delay * self.jitter_ratio
        return max(0.0, exp_delay + random.uniform(-jitter, jitter))


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout_sec: float = 30.0
    _failures: int = 0
    _opened_at: float | None = None

    def allow_request(self) -> bool:
        if self._opened_at is None:
            return True
        return (time.monotonic() - self._opened_at) >= self.recovery_timeout_sec

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._opened_at = time.monotonic()

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        return not self.allow_request()
