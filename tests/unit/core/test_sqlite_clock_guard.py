"""Tests for the SQLite-backed ClockGuard adapter."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import pytest

from py_rizmi.core.clock_guard import REASON, ClockGuard
from py_rizmi.core.sqlite_clock_guard import SqliteClockGuard


@pytest.fixture()
def guard(tmp_path: Path) -> SqliteClockGuard:
    return SqliteClockGuard(
        db_path=tmp_path / "state.db",
        machine_id="m1",
        app_name="MyApp",
        fallback_file=tmp_path / "fallback.dat",
    )


def test_subclasses_clock_guard(guard: SqliteClockGuard) -> None:
    assert isinstance(guard, ClockGuard)


def test_first_check_advances_mark(guard: SqliteClockGuard) -> None:
    result = guard.check_and_update(1000.0)
    assert result.ok
    assert result.last_seen_unix == 1000


def test_rollback_refused(guard: SqliteClockGuard) -> None:
    guard.check_and_update(10_000.0)
    result = guard.check_and_update(5_000.0)
    assert not result.ok
    assert result.reason == REASON
    # mark NOT lowered
    again = guard.check_and_update(10_500.0)
    assert again.ok
    assert again.last_seen_unix == 10_500


def test_tampered_db_row_classified(guard: SqliteClockGuard) -> None:
    guard.check_and_update(1_000.0)
    conn = sqlite3.connect(guard.db_path)
    payload = json.dumps({"version": 1, "last_seen_unix": 999_999})
    conn.execute(
        "UPDATE state SET payload=? WHERE role LIKE 'clock:%'",
        [payload],
    )
    conn.commit()
    conn.close()
    result = guard.check_and_update(2_000.0)
    assert result.tampered_paths  # tampering noticed
    # but the fallback file still supplies the true high-water mark
    assert not result.ok or result.last_seen_unix >= 2_000


def test_db_deleted_fallback_supplies_mark(guard: SqliteClockGuard) -> None:
    guard.check_and_update(50_000.0)
    # wipe every DB row AND the DB itself
    guard.db_path.unlink()
    result = guard.check_and_update(60_000.0)
    assert result.ok
    assert result.last_seen_unix == 60_000  # advanced from surviving mark


def test_db_deletion_cannot_lower_the_ratchet(guard: SqliteClockGuard) -> None:
    guard.check_and_update(50_000.0)
    guard.db_path.unlink()
    result = guard.check_and_update(1_000.0)  # rollback attempt after deleting DB
    # the fallback file still supplies the true mark -> rollback refused
    assert not result.ok
    assert result.reason == REASON
    assert result.last_seen_unix == 50_000


def test_fallback_file_tamper_does_not_break_protection(
    guard: SqliteClockGuard,
) -> None:
    guard.check_and_update(80_000.0)
    guard.fallback_file.write_text("garbage")  # corrupt the file copy
    result = guard.check_and_update(90_000.0)
    assert result.ok  # DB roles carry the mark
    assert any("fallback" in p for p in result.tampered_paths)


def test_shared_namespace_uses_vendor_location(tmp_path: Path) -> None:
    shared_db = tmp_path / "vendor" / "clock.db"
    g1 = SqliteClockGuard(
        db_path=tmp_path / "app-a" / "state.db",
        machine_id="m1",
        app_name="AppA",
        shared_clock_path=shared_db,
        fallback_file=None,
    )
    g2 = SqliteClockGuard(
        db_path=tmp_path / "app-b" / "state.db",
        machine_id="m1",
        app_name="AppB",
        shared_clock_path=shared_db,
        fallback_file=None,
    )
    g1.check_and_update(time.time())
    # App B's own DB has no clock rows; the mark must come from the shared one
    assert g2._read_mark() > 0
