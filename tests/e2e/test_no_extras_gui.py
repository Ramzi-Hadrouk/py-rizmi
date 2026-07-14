"""e2e: Phase 5.2 — `rizmi gui` friendly-error path when [gui] extra is absent.

This test is the permanent regression guard that ensures `rizmi gui` never
silently lets a raw ModuleNotFoundError propagate when PyQt6 is not installed.
It simulates a no-extras environment by patching builtins.__import__ to raise
ModuleNotFoundError for any PyQt6 import, then invokes the CLI via Typer's
CliRunner and asserts the friendly error message and correct exit code.
"""
from __future__ import annotations

import builtins
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from py_rizmi.cli.app import app

runner = CliRunner()

_MISSING_MSG = "pip install py-rizmi[gui]"
_QT_MODULE = "PyQt6"


def _import_blocker(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
    """Raise ModuleNotFoundError for any PyQt6 import, pass everything else through."""
    if name.startswith(_QT_MODULE):
        raise ModuleNotFoundError(f"No module named '{name}'", name=name)
    return _real_import(name, *args, **kwargs)


_real_import = builtins.__import__


class TestRizmiGuiNoExtras:
    """rizmi gui should fail gracefully when PyQt6 is not installed."""

    def test_exits_with_code_1(self) -> None:
        """Exit code must be 1, never 0, when the GUI extra is missing."""
        with patch("builtins.__import__", side_effect=_import_blocker):
            result = runner.invoke(app, ["gui"])
        assert result.exit_code == 1, (
            f"Expected exit code 1, got {result.exit_code}.\nOutput:\n{result.output}"
        )

    def test_friendly_message_shown(self) -> None:
        """Output must contain the install hint so the user knows what to do."""
        with patch("builtins.__import__", side_effect=_import_blocker):
            result = runner.invoke(app, ["gui"])
        assert _MISSING_MSG in result.output, (
            f"Expected '{_MISSING_MSG}' in output, got:\n{result.output}"
        )

    def test_no_raw_traceback(self) -> None:
        """A raw ModuleNotFoundError traceback must NOT reach the user."""
        with patch("builtins.__import__", side_effect=_import_blocker):
            result = runner.invoke(app, ["gui"])
        assert "Traceback" not in result.output, (
            "A raw Python traceback reached the user output — this must be caught.\n"
            f"Output:\n{result.output}"
        )

    def test_missing_module_name_shown(self) -> None:
        """Output must mention which module is missing (PyQt6) for easier diagnosis."""
        with patch("builtins.__import__", side_effect=_import_blocker):
            result = runner.invoke(app, ["gui"])
        assert _QT_MODULE in result.output, (
            f"Expected '{_QT_MODULE}' to be mentioned in output, got:\n{result.output}"
        )
