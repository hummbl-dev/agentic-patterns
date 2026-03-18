"""Smoke tests for examples — verify they run without crashing."""

import subprocess
import sys
from pathlib import Path

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def test_failure_injection_runs():
    result = subprocess.run(
        [sys.executable, str(EXAMPLES_DIR / "failure_injection.py")],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "CLOSED" in result.stdout

def test_agent_runner_runs():
    result = subprocess.run(
        [sys.executable, str(EXAMPLES_DIR / "agent_runner.py")],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "Bus log" in result.stdout
