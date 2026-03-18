"""Health Probe — Interface for system health checking.

Defines a minimal probe interface and collector for aggregating
health status across multiple system components.

Usage:
    from agentic_patterns.health_probe import HealthCollector, HealthProbe, ProbeResult

    class DatabaseProbe(HealthProbe):
        @property
        def name(self) -> str:
            return "database"

        def check(self) -> ProbeResult:
            try:
                db.ping()
                return ProbeResult(name=self.name, healthy=True, message="OK")
            except Exception as e:
                return ProbeResult(name=self.name, healthy=False, message=str(e))

    collector = HealthCollector([DatabaseProbe(), CacheProbe()])
    report = collector.check_all()
    print(report.overall_healthy, report.results)

Stdlib-only.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """Result of a single health probe check."""
    name: str
    healthy: bool
    message: str = ""
    latency_ms: float = 0.0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            object.__setattr__(
                self, "timestamp",
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )


class HealthProbe(ABC):
    """Abstract base for health probes."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this probe."""

    @abstractmethod
    def check(self) -> ProbeResult:
        """Execute the health check and return a result."""


@dataclass(frozen=True, slots=True)
class HealthReport:
    """Aggregated health report from all probes."""
    overall_healthy: bool
    results: list[ProbeResult]
    checked_at: str = ""

    def __post_init__(self):
        if not self.checked_at:
            object.__setattr__(
                self, "checked_at",
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )


class HealthCollector:
    """Runs multiple probes and aggregates results."""

    def __init__(self, probes: list[HealthProbe] | None = None):
        self._probes: list[HealthProbe] = probes or []

    def register(self, probe: HealthProbe) -> None:
        """Register a probe for health checking."""
        self._probes.append(probe)

    def check_all(self) -> HealthReport:
        """Run all registered probes and return an aggregated report."""
        results: list[ProbeResult] = []
        for probe in self._probes:
            start = time.monotonic()
            try:
                result = probe.check()
            except Exception as e:
                result = ProbeResult(
                    name=probe.name,
                    healthy=False,
                    message=f"Probe crashed: {e}",
                )
            elapsed_ms = (time.monotonic() - start) * 1000
            # Inject latency if the probe didn't set it
            if result.latency_ms == 0.0:
                result = ProbeResult(
                    name=result.name,
                    healthy=result.healthy,
                    message=result.message,
                    latency_ms=round(elapsed_ms, 2),
                    timestamp=result.timestamp,
                )
            results.append(result)

        overall = all(r.healthy for r in results) if results else True
        return HealthReport(overall_healthy=overall, results=results)
