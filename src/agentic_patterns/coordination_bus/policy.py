"""Bus Policy — Security policy levels for bus operations.

Usage:
    from agentic_patterns.coordination_bus.policy import PolicyLevel

    policy = PolicyLevel.WARN
    if policy == PolicyLevel.STRICT:
        raise SecurityError("Unsigned messages rejected")

Stdlib-only.
"""

from __future__ import annotations

from enum import Enum, auto


class PolicyLevel(Enum):
    """Security policy levels for bus message validation."""
    PERMISSIVE = auto()  # Accept all messages, no validation
    WARN = auto()        # Accept all, log warnings for unsigned
    STRICT = auto()      # Reject unsigned messages
