#!/usr/bin/env python3
"""Demo: Circuit breaker failure injection and recovery.

Demonstrates the full lifecycle: CLOSED -> OPEN -> HALF_OPEN -> CLOSED.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentic_patterns.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitBreakerState,
)

call_count = 0


def unreliable_service(should_fail: bool = True) -> str:
    global call_count
    call_count += 1
    if should_fail:
        raise ConnectionError(f"Call #{call_count} failed")
    return f"Call #{call_count} succeeded"


def main():
    transitions: list[str] = []

    breaker = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=1.0,  # Short timeout for demo
        on_state_change=lambda old, new: transitions.append(f"{old.name} -> {new.name}"),
    )

    print("=== Phase 1: Inducing failures until breaker trips ===")
    for i in range(5):
        try:
            breaker.call(unreliable_service, True)
        except CircuitBreakerOpen:
            print(f"  Call {i+1}: REJECTED (breaker open)")
        except ConnectionError:
            print(f"  Call {i+1}: FAILED (state={breaker.state.name}, failures={breaker.failure_count})")

    print(f"\nBreaker state: {breaker.state.name}")
    assert breaker.state == CircuitBreakerState.OPEN

    print("\n=== Phase 2: Waiting for recovery timeout ===")
    time.sleep(1.1)
    print(f"Breaker state after wait: {breaker.state.name}")
    assert breaker.state == CircuitBreakerState.HALF_OPEN

    print("\n=== Phase 3: Recovery probe succeeds ===")
    try:
        result = breaker.call(unreliable_service, False)
        print(f"  Probe: {result}")
    except CircuitBreakerOpen:
        print("  Probe: REJECTED (shouldn't happen)")

    print(f"Breaker state after recovery: {breaker.state.name}")
    assert breaker.state == CircuitBreakerState.CLOSED

    print(f"\n=== State transitions ===")
    for t in transitions:
        print(f"  {t}")

    print(f"\nTotal calls: {call_count}")
    print(f"Final state: {breaker.state.name}")
    print(f"Success count: {breaker.success_count}")


if __name__ == "__main__":
    main()
