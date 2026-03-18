"""Tests for circuit breaker."""

import time
import pytest
from agentic_patterns.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitBreakerState,
)


class TestCircuitBreakerStates:
    def test_starts_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_trips_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=2)
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(self._fail)
        assert cb.state == CircuitBreakerState.OPEN

    def test_open_rejects_calls(self):
        cb = CircuitBreaker(failure_threshold=1)
        with pytest.raises(ValueError):
            cb.call(self._fail)
        with pytest.raises(CircuitBreakerOpen):
            cb.call(self._succeed)

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        with pytest.raises(ValueError):
            cb.call(self._fail)
        assert cb.state == CircuitBreakerState.OPEN
        time.sleep(0.15)
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_recovery_on_probe_success(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        with pytest.raises(ValueError):
            cb.call(self._fail)
        time.sleep(0.15)
        result = cb.call(self._succeed)
        assert result == "ok"
        assert cb.state == CircuitBreakerState.CLOSED

    def test_probe_failure_returns_to_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        with pytest.raises(ValueError):
            cb.call(self._fail)
        time.sleep(0.15)
        with pytest.raises(ValueError):
            cb.call(self._fail)
        assert cb.state == CircuitBreakerState.OPEN

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3)
        with pytest.raises(ValueError):
            cb.call(self._fail)
        assert cb.failure_count == 1
        cb.call(self._succeed)
        assert cb.failure_count == 0

    def test_manual_reset(self):
        cb = CircuitBreaker(failure_threshold=1)
        with pytest.raises(ValueError):
            cb.call(self._fail)
        assert cb.state == CircuitBreakerState.OPEN
        cb.reset()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_callback_fires_on_transition(self):
        transitions = []
        cb = CircuitBreaker(
            failure_threshold=1,
            on_state_change=lambda old, new: transitions.append((old, new)),
        )
        with pytest.raises(ValueError):
            cb.call(self._fail)
        assert len(transitions) == 1
        assert transitions[0] == (CircuitBreakerState.CLOSED, CircuitBreakerState.OPEN)

    def test_callback_error_swallowed(self):
        def bad_callback(old, new):
            raise RuntimeError("callback crash")
        cb = CircuitBreaker(failure_threshold=1, on_state_change=bad_callback)
        with pytest.raises(ValueError):
            cb.call(self._fail)
        # Should not crash — callback error swallowed
        assert cb.state == CircuitBreakerState.OPEN

    def test_invalid_threshold(self):
        with pytest.raises(ValueError):
            CircuitBreaker(failure_threshold=0)

    def test_invalid_timeout(self):
        with pytest.raises(ValueError):
            CircuitBreaker(recovery_timeout=-1)

    @staticmethod
    def _fail():
        raise ValueError("intentional failure")

    @staticmethod
    def _succeed():
        return "ok"
