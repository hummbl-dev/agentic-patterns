# Agentic Patterns

Stdlib-only safety patterns for agentic AI systems. Zero third-party runtime dependencies.

Built from production experience coordinating 5+ AI agents (Claude, Codex, Gemini) in a governed execution environment with 6,000+ tests.

## Patterns

| Pattern | Module | What it does |
|---------|--------|-------------|
| **Circuit Breaker** | `circuit_breaker` | Automatic failure detection and recovery. CLOSED/OPEN/HALF_OPEN state machine. |
| **Kill Switch** | `kill_switch` | Emergency halt with 4 modes (DISENGAGED/HALT_NONCRITICAL/HALT_ALL/EMERGENCY). |
| **Coordination Bus** | `coordination_bus` | Append-only TSV message bus with flock locking and HMAC signing. |
| **Schema Validator** | `schema_validator` | JSON Schema validation (Draft 2020-12 subset) without jsonschema dependency. |
| **Health Probe** | `health_probe` | Composable health check interface with latency tracking. |

## Quick Start

```bash
git clone https://github.com/hummbl-dev/agentic-patterns.git
cd agentic-patterns
pip install -e ".[test]"
python -m pytest tests/ -v
```

Try the examples:
```bash
python examples/failure_injection.py   # Circuit breaker lifecycle demo
python examples/agent_runner.py        # Full agent with guardrails
```

## Usage

### Circuit Breaker

```python
from agentic_patterns.circuit_breaker import CircuitBreaker, CircuitBreakerOpen

breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

try:
    result = breaker.call(external_api, request)
except CircuitBreakerOpen:
    result = cached_fallback
```

### Kill Switch

```python
from agentic_patterns.kill_switch import KillSwitch, KillSwitchMode

ks = KillSwitch(critical_tasks=frozenset({"health_check", "alerting"}))
ks.engage(KillSwitchMode.HALT_NONCRITICAL, reason="Error rate spike")

if ks.is_task_allowed("data_export"):
    run_export()  # Blocked during HALT_NONCRITICAL
```

### Coordination Bus

```python
from agentic_patterns.coordination_bus import BusWriter, sign_message

bus = BusWriter("coordination.tsv")
bus.post("agent-1", "all", "STATUS", "Task complete")

# Optional: sign messages for tamper detection
secret = "shared-secret"
sig = sign_message("payload", secret)
```

### Schema Validator

```python
from agentic_patterns.schema_validator import validate, ValidationError

schema = {
    "type": "object",
    "required": ["name", "status"],
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "status": {"type": "string", "enum": ["active", "inactive"]},
    },
}

validate({"name": "agent-1", "status": "active"}, schema)  # OK
```

### Health Probes

```python
from agentic_patterns.health_probe import HealthCollector, HealthProbe, ProbeResult

class APIProbe(HealthProbe):
    @property
    def name(self): return "external-api"

    def check(self):
        # Your health check logic
        return ProbeResult(name=self.name, healthy=True, message="200 OK")

collector = HealthCollector([APIProbe()])
report = collector.check_all()
print(report.overall_healthy)  # True
```

## Why Stdlib-Only?

Every pattern in this library uses only Python's standard library. No `requests`, no `pydantic`, no `jsonschema`.

This constraint is intentional:
- **Zero supply chain risk** for safety-critical components
- **No version conflicts** with the host application
- **Deployable anywhere** Python 3.11+ runs
- **Auditable** -- the entire dependency tree is Python itself

## Architecture

```
Agent Task
    |
    v
[Kill Switch] -- Is this task allowed?
    |
    v
[Circuit Breaker] -- Is the downstream service healthy?
    |
    v
[External Call] -- Execute with failure tracking
    |
    v
[Bus Writer] -- Log the event (append-only, signed)
    |
    v
[Health Probe] -- Report status to collectors
```

## Requirements

- Python 3.11+
- Unix-like OS for coordination bus (uses `fcntl.flock`)
- No runtime dependencies

## HUMMBL Ecosystem

This repo is part of the [HUMMBL](https://github.com/hummbl-dev) cognitive AI architecture. Related repos:

| Repo | Purpose |
|------|---------|
| [hummbl-governance](https://github.com/hummbl-dev/hummbl-governance) | Production governance runtime built on these patterns |
| [base120](https://github.com/hummbl-dev/base120) | Deterministic cognitive framework -- 120 mental models across 6 transformations |
| [mcp-server](https://github.com/hummbl-dev/mcp-server) | Model Context Protocol server for Base120 integration |
| [arbiter](https://github.com/hummbl-dev/arbiter) | Agent-aware code quality scoring and attribution |
| [governed-iac-reference](https://github.com/hummbl-dev/governed-iac-reference) | Reference architecture for governed infrastructure-as-code |

Learn more at [hummbl.io](https://hummbl.io).

## License

MIT -- see [LICENSE](LICENSE).
