"""Tests for coordination bus."""

import tempfile
from pathlib import Path

import pytest
from agentic_patterns.coordination_bus.writer import BusWriter
from agentic_patterns.coordination_bus.signing import (
    generate_secret,
    sign_message,
    verify_message,
)
from agentic_patterns.coordination_bus.policy import PolicyLevel


class TestBusWriter:
    def test_post_and_read(self):
        bus_path = Path(tempfile.mkdtemp()) / "test_bus.tsv"
        bus = BusWriter(bus_path)
        bus.post("agent-1", "all", "STATUS", "Hello world")
        messages = bus.read_all()
        assert len(messages) == 1
        assert messages[0]["from"] == "agent-1"
        assert messages[0]["to"] == "all"
        assert messages[0]["type"] == "STATUS"
        assert messages[0]["message"] == "Hello world"

    def test_multiple_messages(self):
        bus_path = Path(tempfile.mkdtemp()) / "test_bus.tsv"
        bus = BusWriter(bus_path)
        bus.post("a", "b", "T1", "msg1")
        bus.post("c", "d", "T2", "msg2")
        messages = bus.read_all()
        assert len(messages) == 2

    def test_sanitizes_tabs_and_newlines(self):
        bus_path = Path(tempfile.mkdtemp()) / "test_bus.tsv"
        bus = BusWriter(bus_path)
        bus.post("agent\t1", "all", "STATUS", "line1\nline2")
        messages = bus.read_all()
        assert len(messages) == 1
        assert "\t" not in messages[0]["from"]
        assert "\n" not in messages[0]["message"]

    def test_creates_parent_dirs(self):
        bus_path = Path(tempfile.mkdtemp()) / "nested" / "deep" / "bus.tsv"
        bus = BusWriter(bus_path)
        bus.post("a", "b", "T", "m")
        assert bus_path.exists()

    def test_read_empty_bus(self):
        bus_path = Path(tempfile.mkdtemp()) / "empty.tsv"
        bus = BusWriter(bus_path)
        assert bus.read_all() == []

    def test_read_nonexistent_bus(self):
        bus_path = Path(tempfile.mkdtemp()) / "nonexistent.tsv"
        bus = BusWriter(bus_path)
        assert bus.read_all() == []

    def test_timestamp_format(self):
        bus_path = Path(tempfile.mkdtemp()) / "ts.tsv"
        bus = BusWriter(bus_path)
        bus.post("a", "b", "T", "m")
        msg = bus.read_all()[0]
        assert msg["timestamp"].endswith("Z")
        assert "T" in msg["timestamp"]


class TestMessageSigning:
    def test_sign_and_verify(self):
        secret = "test-secret"
        payload = "hello world"
        sig = sign_message(payload, secret)
        assert verify_message(payload, sig, secret)

    def test_wrong_secret_fails(self):
        sig = sign_message("payload", "secret-1")
        assert not verify_message("payload", sig, "secret-2")

    def test_tampered_payload_fails(self):
        secret = "secret"
        sig = sign_message("original", secret)
        assert not verify_message("tampered", sig, secret)

    def test_generate_secret_length(self):
        secret = generate_secret(16)
        assert len(secret) == 32  # hex encoding doubles the length

    def test_generate_secret_unique(self):
        s1 = generate_secret()
        s2 = generate_secret()
        assert s1 != s2


class TestPolicyLevel:
    def test_levels_exist(self):
        assert PolicyLevel.PERMISSIVE
        assert PolicyLevel.WARN
        assert PolicyLevel.STRICT

    def test_comparison(self):
        assert PolicyLevel.PERMISSIVE != PolicyLevel.STRICT
