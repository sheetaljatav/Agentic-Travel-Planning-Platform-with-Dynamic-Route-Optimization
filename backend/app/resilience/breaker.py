"""Minimal async per-host circuit breaker (closed / open / half-open).

Ported conceptually from the legacy util/circuit.ts. One implementation, async.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.config import settings
from app.resilience.errors import CircuitOpenError


@dataclass
class _BreakerState:
    failures: int = 0
    opened_at: float = 0.0
    half_open: bool = False


@dataclass
class CircuitBreaker:
    fail_threshold: int = field(default_factory=lambda: settings.breaker_fail_threshold)
    reset_s: float = field(default_factory=lambda: settings.breaker_reset_s)
    _hosts: dict[str, _BreakerState] = field(default_factory=dict)

    def _state(self, host: str) -> _BreakerState:
        return self._hosts.setdefault(host, _BreakerState())

    def before(self, host: str) -> None:
        """Raise CircuitOpenError if the host's circuit is open and not ready."""
        st = self._state(host)
        if st.opened_at == 0.0:
            return
        if time.monotonic() - st.opened_at >= self.reset_s:
            st.half_open = True  # allow a single trial request through
            return
        raise CircuitOpenError(host)

    def on_success(self, host: str) -> None:
        st = self._state(host)
        st.failures = 0
        st.opened_at = 0.0
        st.half_open = False

    def on_failure(self, host: str) -> None:
        st = self._state(host)
        if st.half_open:  # trial failed -> re-open immediately
            st.opened_at = time.monotonic()
            st.half_open = False
            return
        st.failures += 1
        if st.failures >= self.fail_threshold:
            st.opened_at = time.monotonic()


breaker = CircuitBreaker()
