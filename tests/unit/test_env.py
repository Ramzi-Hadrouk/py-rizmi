"""Tests for frozen-environment detection."""
from __future__ import annotations

import sys
from unittest import mock

from py_rizmi._internal.env import is_frozen, packager


def test_not_frozen_under_pytest() -> None:
    assert is_frozen() is False
    assert packager() == "none"


def test_detects_pyinstaller() -> None:
    with mock.patch.object(sys, "frozen", True, create=True):
        assert is_frozen() is True
        assert packager() == "pyinstaller"


def test_detects_nuitka() -> None:
    fake_main = mock.MagicMock()
    fake_main.__compiled__ = True  # type: ignore[attr-defined]
    with mock.patch.dict(sys.modules, {"__main__": fake_main}):
        assert is_frozen() is True
        assert packager() == "nuitka"
