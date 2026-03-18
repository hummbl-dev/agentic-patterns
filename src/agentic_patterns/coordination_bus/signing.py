"""Message Signing — HMAC-SHA256 signing and verification for bus messages.

Usage:
    from agentic_patterns.coordination_bus.signing import sign_message, verify_message

    secret = "my-shared-secret"
    payload = "2026-03-18T12:00:00Z\\tagent-1\\tall\\tSTATUS\\tOK"
    signature = sign_message(payload, secret)
    assert verify_message(payload, signature, secret)

Stdlib-only.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets


def generate_secret(nbytes: int = 32) -> str:
    """Generate a cryptographically secure random secret (hex-encoded)."""
    return secrets.token_hex(nbytes)


def sign_message(payload: str, secret: str) -> str:
    """Sign a payload with HMAC-SHA256. Returns hex digest."""
    return hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_message(payload: str, signature: str, secret: str) -> bool:
    """Verify an HMAC-SHA256 signature. Uses constant-time comparison."""
    expected = sign_message(payload, secret)
    return hmac.compare_digest(expected, signature)
