"""Bus Writer — Append-only TSV message bus with file locking.

Provides a simple, crash-safe message bus using TSV (tab-separated values)
with flock-based mutual exclusion. Messages are append-only — no edits,
no deletes.

Format: timestamp_utc\\tfrom\\tto\\ttype\\tmessage\\n

Usage:
    from agentic_patterns.coordination_bus import BusWriter

    bus = BusWriter("messages.tsv")
    bus.post("agent-1", "all", "STATUS", "Starting task")

Unix-only (uses fcntl.flock). Stdlib-only.
"""

from __future__ import annotations

import fcntl
import os
from datetime import datetime, timezone
from pathlib import Path


class BusWriter:
    """Append-only TSV message bus with file-level locking.

    Args:
        bus_path: Path to the TSV file. Created if it doesn't exist.
    """

    def __init__(self, bus_path: str | Path):
        self._bus_path = Path(bus_path)

    @property
    def bus_path(self) -> Path:
        return self._bus_path

    def post(
        self,
        from_id: str,
        to_id: str,
        msg_type: str,
        message: str,
    ) -> None:
        """Append a message to the bus file.

        Uses fcntl.flock(LOCK_EX) for safe concurrent writes from
        multiple processes.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Sanitize: no tabs or newlines in fields
        fields = [timestamp, from_id, to_id, msg_type, message]
        sanitized = [f.replace("\t", " ").replace("\n", " ").replace("\r", "") for f in fields]
        line = "\t".join(sanitized) + "\n"

        self._bus_path.parent.mkdir(parents=True, exist_ok=True)

        fd = os.open(str(self._bus_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            os.write(fd, line.encode("utf-8"))
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def read_all(self) -> list[dict[str, str]]:
        """Read all messages from the bus. Returns list of dicts."""
        if not self._bus_path.exists():
            return []

        messages: list[dict[str, str]] = []
        with open(self._bus_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 5:
                    messages.append({
                        "timestamp": parts[0],
                        "from": parts[1],
                        "to": parts[2],
                        "type": parts[3],
                        "message": parts[4],
                    })
        return messages
