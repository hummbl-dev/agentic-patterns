"""Kill Switch — Emergency halt for agentic systems.

Four operational modes with escalating restrictions:
  DISENGAGED     → Normal operation, all tasks allowed.
  HALT_NONCRITICAL → Only critical tasks proceed.
  HALT_ALL       → All tasks blocked except kill-switch management.
  EMERGENCY      → Full system halt, no exceptions.

Usage:
    from agentic_patterns.kill_switch import KillSwitch, KillSwitchMode

    ks = KillSwitch()
    ks.engage(KillSwitchMode.HALT_NONCRITICAL, reason="High error rate")

    if ks.is_task_allowed("data_processing"):
        run_task()
    else:
        print(f"Task blocked: {ks.mode.name}")

Thread-safe. Stdlib-only.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable

logger = logging.getLogger(__name__)


class KillSwitchMode(Enum):
    """Kill switch operational modes, ordered by severity."""
    DISENGAGED = auto()
    HALT_NONCRITICAL = auto()
    HALT_ALL = auto()
    EMERGENCY = auto()


class KillSwitchEngaged(Exception):
    """Raised when a task is blocked by the kill switch."""

    def __init__(self, mode: KillSwitchMode, task: str, reason: str = ""):
        self.mode = mode
        self.task = task
        self.reason = reason
        super().__init__(f"Kill switch {mode.name}: task '{task}' blocked. {reason}")


@dataclass(frozen=True, slots=True)
class KillSwitchEvent:
    """Immutable record of a kill switch state change."""
    timestamp: str
    old_mode: KillSwitchMode
    new_mode: KillSwitchMode
    reason: str
    actor: str


class KillSwitch:
    """Emergency halt control for agentic task execution.

    Args:
        critical_tasks: Set of task names that are allowed during HALT_NONCRITICAL.
        on_mode_change: Optional callback(event) on mode transitions.
    """

    def __init__(
        self,
        critical_tasks: frozenset[str] | None = None,
        on_mode_change: Callable[[KillSwitchEvent], None] | None = None,
    ):
        self._mode = KillSwitchMode.DISENGAGED
        self._reason = ""
        self._critical_tasks = critical_tasks or frozenset({"health_check", "kill_switch_manage"})
        self._on_mode_change = on_mode_change
        self._event_log: list[KillSwitchEvent] = []
        self._lock = threading.RLock()

    @property
    def mode(self) -> KillSwitchMode:
        with self._lock:
            return self._mode

    @property
    def reason(self) -> str:
        with self._lock:
            return self._reason

    @property
    def event_log(self) -> list[KillSwitchEvent]:
        with self._lock:
            return list(self._event_log)

    @property
    def is_engaged(self) -> bool:
        with self._lock:
            return self._mode != KillSwitchMode.DISENGAGED

    def engage(
        self,
        mode: KillSwitchMode,
        reason: str = "",
        actor: str = "system",
    ) -> None:
        """Engage the kill switch at the specified mode."""
        if mode == KillSwitchMode.DISENGAGED:
            raise ValueError("Use disengage() to return to normal operation")

        with self._lock:
            old = self._mode
            if old == mode:
                return
            self._mode = mode
            self._reason = reason
            event = KillSwitchEvent(
                timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                old_mode=old,
                new_mode=mode,
                reason=reason,
                actor=actor,
            )
            self._event_log.append(event)
            self._fire_callback(event)

    def disengage(self, reason: str = "", actor: str = "system") -> None:
        """Return to normal operation."""
        with self._lock:
            old = self._mode
            if old == KillSwitchMode.DISENGAGED:
                return
            self._mode = KillSwitchMode.DISENGAGED
            self._reason = ""
            event = KillSwitchEvent(
                timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                old_mode=old,
                new_mode=KillSwitchMode.DISENGAGED,
                reason=reason,
                actor=actor,
            )
            self._event_log.append(event)
            self._fire_callback(event)

    def is_task_allowed(self, task_name: str) -> bool:
        """Check if a task is allowed under the current mode."""
        with self._lock:
            if self._mode == KillSwitchMode.DISENGAGED:
                return True
            if self._mode == KillSwitchMode.HALT_NONCRITICAL:
                return task_name in self._critical_tasks
            # HALT_ALL and EMERGENCY block everything
            return False

    def check_or_raise(self, task_name: str) -> None:
        """Raise KillSwitchEngaged if the task is not allowed."""
        if not self.is_task_allowed(task_name):
            raise KillSwitchEngaged(self._mode, task_name, self._reason)

    def _fire_callback(self, event: KillSwitchEvent) -> None:
        if self._on_mode_change is None:
            return
        try:
            self._on_mode_change(event)
        except Exception:
            logger.debug("Kill switch callback failed", exc_info=True)
