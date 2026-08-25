"""Tests for app-scoped path resolution and fallback filenames."""
from __future__ import annotations

from py_rizmi.core.state_store import StateStore
from py_rizmi.integrations.validation import _obfuscated_name


def test_default_db_path_is_app_scoped_and_writable_looking() -> None:
    path = StateStore.default_path("MyProduct")
    assert "MyProduct" in str(path)
    assert path.name == "state.db"
    lowered = str(path).lower()
    assert "site-packages" not in lowered
    assert "_meipass" not in lowered


def test_obfuscated_name_includes_app_name() -> None:
    a = _obfuscated_name("AppA", "primary", True)
    b = _obfuscated_name("AppB", "primary", True)
    c = _obfuscated_name("AppA", "fallback", True)
    # distinct apps -> distinct names even if the file lands in a shared dir
    assert a != b
    # distinct roles within one app -> distinct names
    assert a != c
    # deterministic
    assert a == _obfuscated_name("AppA", "primary", True)
    assert a.startswith(".") and a.endswith(".dat")


def test_obfuscated_name_windows_variant_has_no_dot() -> None:
    name = _obfuscated_name("AppA", "primary", False)
    assert not name.startswith(".")
