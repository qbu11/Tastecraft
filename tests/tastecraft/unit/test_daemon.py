"""Unit tests for daemon status/stop commands."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from tastecraft.cli.commands.daemon import (
    _is_process_alive,
    _kill_process,
    _read_pid,
    _remove_pid,
    _write_pid,
)


class TestPidFile:
    def test_write_and_read(self, tmp_path: object) -> None:
        pid_file = str(tmp_path) + "/daemon.pid"  # type: ignore[operator]
        with patch("tastecraft.cli.commands.daemon._pid_file", return_value=pid_file):
            _write_pid(12345)
            assert _read_pid() == 12345

    def test_read_nonexistent(self, tmp_path: object) -> None:
        pid_file = str(tmp_path) + "/nonexistent.pid"  # type: ignore[operator]
        with patch("tastecraft.cli.commands.daemon._pid_file", return_value=pid_file):
            assert _read_pid() is None

    def test_remove(self, tmp_path: object) -> None:
        pid_file = str(tmp_path) + "/daemon.pid"  # type: ignore[operator]
        with patch("tastecraft.cli.commands.daemon._pid_file", return_value=pid_file):
            _write_pid(99999)
            _remove_pid()
            assert _read_pid() is None

    def test_remove_nonexistent(self, tmp_path: object) -> None:
        pid_file = str(tmp_path) + "/nope.pid"  # type: ignore[operator]
        with patch("tastecraft.cli.commands.daemon._pid_file", return_value=pid_file):
            # Should not raise
            _remove_pid()


class TestProcessAlive:
    def test_current_process_is_alive(self) -> None:
        assert _is_process_alive(os.getpid()) is True

    def test_nonexistent_pid(self) -> None:
        # PID 99999999 is extremely unlikely to exist
        assert _is_process_alive(99999999) is False
