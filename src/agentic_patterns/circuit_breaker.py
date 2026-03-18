"""Circuit Breaker — Automatic failure detection and recovery.

Three-state machine that protects callers from cascading failures:
  CLOSED  → Normal. Failures counted. Trips to OPEN at threshold.
  OPEN    → All calls rejected. After recovery timeout, transitions to HALF_OPEN.
  HALF_OPEN → One probe call allowed. Success resets to CLOSED; failure returns to OPEN.

Usage:
    from agentic_patterns.circuit_breaker import CircuitBreaker, CircuitBreakerOpen

    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=10.0)
    try:
        result = breaker.call(external_service, arg1, arg2)
    except CircuitBreakerOpen:
        result = fallback_value

Thread-safe. Stdlib-only. Zero third-party dependencies.
"""

from __future__ import annotations

import logging
import threading
import time
from enum import Enum, auto
from typing import Any, Callable

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


class CircuitBreakerOpen(Exception):
    """Raised when a call is attempted on an open circuit breaker."""

    def __init__(
        self,
        message: str = "Circuit breaker is open",
        *,
        failure_count: int = 0,
        last_failure_time: float | None = None,
        recovery_timeout: float = 0.0,
    ):
        self.failure_count = failure_count
        self.last_failure_time = last_failure_time
        self.recovery_timeout = recovery_timeout
        super().__init__(message)


class CircuitBreaker:
    """Automatic failure detection and recovery for callable wrappers.

    Args:
        failure_threshold: Consecutive failures before tripping to OPEN.
        recovery_timeout: Seconds in OPEN before allowing a HALF_OPEN probe.
        on_state_change: Optional callback(old_state, new_state) on transitions.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        on_state_change: Callable[[CircuitBreakerState, CircuitBreakerState], None] | None = None,
    ):
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if recovery_timeout < 0:
            raise ValueError("recovery_timeout must be >= 0")

        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._on_state_change = on_state_change

        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._half_open_probe_in_flight = False
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitBreakerState:
        with self._lock:
            return self._effective_state()

    @property
    def failure_count(self) -> int:
        with self._lock:
            return self._failure_count

    @property
    def success_count(self) -> int:
        with self._lock:
            return self._success_count

    def call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute *fn* through the circuit breaker.

        Returns whatever *fn* returns. Raises CircuitBreakerOpen if the
        breaker is OPEN. Re-raises any exception from *fn* after recording
        the failure.
        """
        with self._lock:
            effective = self._effective_state()

            if effective == CircuitBreakerState.OPEN:
                raise CircuitBreakerOpen(
                    f"Circuit breaker is open ({self._failure_count} failures)",
                    failure_count=self._failure_count,
                    last_failure_time=self._last_failure_time,
                    recovery_timeout=self._recovery_timeout,
                )

            if effective == CircuitBreakerState.HALF_OPEN:
                if self._state == CircuitBreakerState.OPEN:
                    self._transition(CircuitBreakerState.HALF_OPEN)
                if self._half_open_probe_in_flight:
                    raise CircuitBreakerOpen(
                        "Half-open probe already in progress",
                        failure_count=self._failure_count,
                        last_failure_time=self._last_failure_time,
                        recovery_timeout=self._recovery_timeout,
                    )
                self._half_open_probe_in_flight = True

        try:
            result = fn(*args, **kwargs)
        except Exception:
            with self._lock:
                self._record_failure()
            raise

        with self._lock:
            self._record_success()
        return result

    def reset(self) -> None:
        """Manually reset to CLOSED state."""
        with self._lock:
            old = self._effective_state()
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            self._half_open_probe_in_flight = False
            if self._state != CircuitBreakerState.CLOSED:
                self._state = CircuitBreakerState.CLOSED
                self._fire_callback(old, CircuitBreakerState.CLOSED)

    def _effective_state(self) -> CircuitBreakerState:
        if self._state == CircuitBreakerState.OPEN and self._last_failure_time is not None:
            if time.monotonic() - self._last_failure_time >= self._recovery_timeout:
                return CircuitBreakerState.HALF_OPEN
        return self._state

    def _record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._half_open_probe_in_flight = False
            self._transition(CircuitBreakerState.OPEN)
        elif self._state == CircuitBreakerState.CLOSED and self._failure_count >= self._failure_threshold:
            self._transition(CircuitBreakerState.OPEN)

    def _record_success(self) -> None:
        self._success_count += 1
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._half_open_probe_in_flight = False
            self._failure_count = 0
            self._last_failure_time = None
            self._transition(CircuitBreakerState.CLOSED)
        elif self._state == CircuitBreakerState.CLOSED:
            self._failure_count = 0

    def _transition(self, new_state: CircuitBreakerState) -> None:
        old = self._state
        if old == new_state:
            return
        self._state = new_state
        self._fire_callback(old, new_state)

    def _fire_callback(self, old: CircuitBreakerState, new: CircuitBreakerState) -> None:
        if self._on_state_change is None:
            return
        try:
            self._on_state_change(old, new)
        except Exception:
            logger.debug("State change callback failed", exc_info=True)
