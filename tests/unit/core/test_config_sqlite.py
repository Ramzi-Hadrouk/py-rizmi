"""Tests for the SQLite store settings on RizmiConfig."""
from __future__ import annotations

import pytest

from py_rizmi.core.config import RizmiConfig


class TestSqliteSettings:
    def test_defaults_are_off(self):
        c = RizmiConfig()
        assert c.use_sqlite is False
        assert c.db_path is None
        assert c.allow_default_namespace is False
        assert c.shared_clock_namespace is False

    def test_use_sqlite_accepts_true(self):
        assert RizmiConfig(use_sqlite=True).use_sqlite is True

    def test_use_sqlite_rejects_non_bool(self):
        with pytest.raises(ValueError, match="use_sqlite"):
            RizmiConfig(use_sqlite="yes")  # type: ignore[arg-type]

    def test_db_path_accepts_string(self):
        c = RizmiConfig(db_path="/tmp/state.db")
        assert c.db_path == "/tmp/state.db"

    def test_db_path_rejects_non_string(self):
        with pytest.raises(ValueError, match="db_path"):
            RizmiConfig(db_path=123)  # type: ignore[arg-type]

    def test_allow_default_namespace_rejects_non_bool(self):
        with pytest.raises(ValueError, match="allow_default_namespace"):
            RizmiConfig(allow_default_namespace=1)  # type: ignore[arg-type]

    def test_shared_clock_namespace_rejects_non_bool(self):
        with pytest.raises(ValueError, match="shared_clock_namespace"):
            RizmiConfig(shared_clock_namespace="on")  # type: ignore[arg-type]

    def test_roundtrip_via_dict_preserves_new_fields(self):
        c = RizmiConfig(use_sqlite=True, db_path="/x/y.db", shared_clock_namespace=True)
        restored = RizmiConfig.from_dict(c.to_dict())
        assert restored.use_sqlite is True
        assert restored.db_path == "/x/y.db"
        assert restored.shared_clock_namespace is True
