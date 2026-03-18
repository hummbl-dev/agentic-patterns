#!/usr/bin/env python3
"""Demo: Agent runner with safety guardrails.

Shows the full pattern: an agent executes tasks protected by a circuit
breaker and kill switch, with all events logged to the coordination bus.
"""

import random
import sys
import tempfile
from pathlib import Path

# Add src to path for demo purposes
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentic_patterns.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from agentic_patterns.kill_switch import KillSwitch, KillSwitchEngaged, KillSwitchMode
from agentic_patterns.coordination_bus import BusWriter


def flaky_external_service(success_rate: float = 0.7) -> str:
    """Simulates an external service that fails intermittently."""
    if random.random() > success_rate:
        raise ConnectionError("Service unavailable")
    return "result-ok"


def main():
    # Setup
    bus_path = Path(tempfile.mkdtemp()) / "demo_bus.tsv"
    bus = BusWriter(bus_path)
    breaker = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=2.0,
        on_state_change=lambda old, new: bus.post(
            "agent-runner", "all", "STATUS",
            f"Circuit breaker: {old.name} -> {new.name}",
        ),
    )
    kill_switch = KillSwitch(
        on_mode_change=lambda event: bus.post(
            event.actor, "all", "STATUS",
            f"Kill switch: {event.old_mode.name} -> {event.new_mode.name} ({event.reason})",
        ),
    )

    bus.post("agent-runner", "all", "STATUS", "Agent starting")

    # Execute tasks
    tasks = ["fetch_data", "process_data", "generate_report", "send_notification", "cleanup"]

    for task_name in tasks:
        # Check kill switch first
        if not kill_switch.is_task_allowed(task_name):
            bus.post("agent-runner", "all", "STATUS", f"Task '{task_name}' blocked by kill switch")
            print(f"  BLOCKED: {task_name} (kill switch: {kill_switch.mode.name})")
            continue

        # Execute through circuit breaker
        try:
            result = breaker.call(flaky_external_service, 0.6)
            bus.post("agent-runner", "all", "STATUS", f"Task '{task_name}' completed: {result}")
            print(f"  OK: {task_name}")
        except CircuitBreakerOpen as e:
            bus.post("agent-runner", "all", "STATUS", f"Task '{task_name}' skipped: breaker open")
            print(f"  SKIPPED: {task_name} (breaker open, {e.failure_count} failures)")
            # Engage kill switch if breaker is open
            if not kill_switch.is_engaged:
                kill_switch.engage(KillSwitchMode.HALT_NONCRITICAL, reason="Circuit breaker open")
                print(f"  >> Kill switch engaged: HALT_NONCRITICAL")
        except ConnectionError as e:
            bus.post("agent-runner", "all", "STATUS", f"Task '{task_name}' failed: {e}")
            print(f"  FAILED: {task_name} ({e})")

    bus.post("agent-runner", "all", "STATUS", "Agent finished")

    # Print bus log
    print(f"\n--- Bus log ({bus_path}) ---")
    for msg in bus.read_all():
        print(f"  [{msg['timestamp']}] {msg['from']} > {msg['to']}: {msg['message']}")

    print(f"\nKill switch events: {len(kill_switch.event_log)}")
    print(f"Circuit breaker state: {breaker.state.name}")
    print(f"Circuit breaker failures: {breaker.failure_count}")


if __name__ == "__main__":
    random.seed(42)  # Reproducible demo
    main()
