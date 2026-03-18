"""Tests for kill switch."""

import pytest
from agentic_patterns.kill_switch import (
    KillSwitch,
    KillSwitchEngaged,
    KillSwitchMode,
)


class TestKillSwitchModes:
    def test_starts_disengaged(self):
        ks = KillSwitch()
        assert ks.mode == KillSwitchMode.DISENGAGED
        assert not ks.is_engaged

    def test_engage_halt_noncritical(self):
        ks = KillSwitch()
        ks.engage(KillSwitchMode.HALT_NONCRITICAL, reason="test")
        assert ks.mode == KillSwitchMode.HALT_NONCRITICAL
        assert ks.is_engaged
        assert ks.reason == "test"

    def test_engage_halt_all(self):
        ks = KillSwitch()
        ks.engage(KillSwitchMode.HALT_ALL)
        assert ks.mode == KillSwitchMode.HALT_ALL

    def test_engage_emergency(self):
        ks = KillSwitch()
        ks.engage(KillSwitchMode.EMERGENCY)
        assert ks.mode == KillSwitchMode.EMERGENCY

    def test_disengage(self):
        ks = KillSwitch()
        ks.engage(KillSwitchMode.HALT_ALL)
        ks.disengage(reason="resolved")
        assert ks.mode == KillSwitchMode.DISENGAGED
        assert not ks.is_engaged

    def test_engage_disengaged_raises(self):
        ks = KillSwitch()
        with pytest.raises(ValueError):
            ks.engage(KillSwitchMode.DISENGAGED)

    def test_double_engage_same_mode_noop(self):
        ks = KillSwitch()
        ks.engage(KillSwitchMode.HALT_ALL)
        ks.engage(KillSwitchMode.HALT_ALL)
        assert len(ks.event_log) == 1  # Only one transition

    def test_double_disengage_noop(self):
        ks = KillSwitch()
        ks.disengage()
        assert len(ks.event_log) == 0


class TestTaskAllowance:
    def test_all_allowed_when_disengaged(self):
        ks = KillSwitch()
        assert ks.is_task_allowed("anything")
        assert ks.is_task_allowed("random_task")

    def test_critical_tasks_allowed_during_halt_noncritical(self):
        ks = KillSwitch(critical_tasks=frozenset({"health_check", "monitoring"}))
        ks.engage(KillSwitchMode.HALT_NONCRITICAL)
        assert ks.is_task_allowed("health_check")
        assert ks.is_task_allowed("monitoring")
        assert not ks.is_task_allowed("data_processing")

    def test_nothing_allowed_during_halt_all(self):
        ks = KillSwitch()
        ks.engage(KillSwitchMode.HALT_ALL)
        assert not ks.is_task_allowed("health_check")
        assert not ks.is_task_allowed("anything")

    def test_nothing_allowed_during_emergency(self):
        ks = KillSwitch()
        ks.engage(KillSwitchMode.EMERGENCY)
        assert not ks.is_task_allowed("health_check")

    def test_check_or_raise(self):
        ks = KillSwitch()
        ks.engage(KillSwitchMode.HALT_ALL)
        with pytest.raises(KillSwitchEngaged) as exc_info:
            ks.check_or_raise("my_task")
        assert exc_info.value.task == "my_task"
        assert exc_info.value.mode == KillSwitchMode.HALT_ALL


class TestEventLog:
    def test_logs_transitions(self):
        ks = KillSwitch()
        ks.engage(KillSwitchMode.HALT_NONCRITICAL, reason="test", actor="admin")
        ks.disengage(reason="resolved", actor="admin")
        log = ks.event_log
        assert len(log) == 2
        assert log[0].new_mode == KillSwitchMode.HALT_NONCRITICAL
        assert log[0].actor == "admin"
        assert log[1].new_mode == KillSwitchMode.DISENGAGED

    def test_callback_fires(self):
        events = []
        ks = KillSwitch(on_mode_change=lambda e: events.append(e))
        ks.engage(KillSwitchMode.HALT_ALL)
        assert len(events) == 1

    def test_callback_error_swallowed(self):
        def bad_callback(event):
            raise RuntimeError("crash")
        ks = KillSwitch(on_mode_change=bad_callback)
        ks.engage(KillSwitchMode.HALT_ALL)  # Should not crash
        assert ks.mode == KillSwitchMode.HALT_ALL
