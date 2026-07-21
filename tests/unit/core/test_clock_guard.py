import base64
import json
from unittest import mock

import pytest

from py_rizmi.core.clock_guard import ClockGuard


# --- Layer 1: persisted anti-rollback high-water mark ----------------------


def test_fresh_install_establishes_baseline(tmp_path):
    guard = ClockGuard(str(tmp_path / "clock.json"), machine_id="M1")
    result = guard.check_and_update(now=1_000_000)
    assert result.ok
    assert result.last_seen_unix == 1_000_000


def test_forward_time_always_ok(tmp_path):
    guard = ClockGuard(str(tmp_path / "clock.json"), machine_id="M1")
    guard.check_and_update(now=1_000_000)
    result = guard.check_and_update(now=1_000_100)
    assert result.ok
    assert result.last_seen_unix == 1_000_100


def test_large_forward_jump_after_long_absence_is_ok(tmp_path):
    guard = ClockGuard(str(tmp_path / "clock.json"), machine_id="M1")
    guard.check_and_update(now=1_000_000)
    result = guard.check_and_update(now=1_000_000 + 60 * 86_400)
    assert result.ok


def test_small_backward_jump_within_tolerance_is_ok(tmp_path):
    guard = ClockGuard(str(tmp_path / "clock.json"), machine_id="M1", tolerance_seconds=300)
    guard.check_and_update(now=1_000_000)
    result = guard.check_and_update(now=1_000_000 - 100)
    assert result.ok


def test_rollback_beyond_tolerance_is_rejected(tmp_path):
    guard = ClockGuard(str(tmp_path / "clock.json"), machine_id="M1", tolerance_seconds=300)
    guard.check_and_update(now=1_000_000)
    result = guard.check_and_update(now=1_000_000 - 10_000)
    assert not result.ok
    assert result.reason == "clock_tampering"


def test_rollback_attempt_does_not_lower_the_high_water_mark(tmp_path):
    guard = ClockGuard(str(tmp_path / "clock.json"), machine_id="M1", tolerance_seconds=300)
    guard.check_and_update(now=1_000_000)
    first_reject = guard.check_and_update(now=1)
    second_reject = guard.check_and_update(now=1)
    assert not first_reject.ok and not second_reject.ok
    assert first_reject.last_seen_unix == second_reject.last_seen_unix == 1_000_000


# --- Redundant storage locations -------------------------------------------


def test_redundant_copies_are_both_written(tmp_path):
    p1, p2 = tmp_path / "a.json", tmp_path / "b.json"
    guard = ClockGuard([str(p1), str(p2)], machine_id="M1")
    guard.check_and_update(now=1_000_000)
    assert p1.exists() and p2.exists()


def test_deleting_one_redundant_copy_does_not_reset_the_ratchet(tmp_path):
    p1, p2 = tmp_path / "a.json", tmp_path / "b.json"
    guard = ClockGuard([str(p1), str(p2)], machine_id="M1", tolerance_seconds=300)
    guard.check_and_update(now=2_000_000)

    p1.unlink()  # simulate a user finding and deleting the "obvious" copy

    guard2 = ClockGuard([str(p1), str(p2)], machine_id="M1", tolerance_seconds=300)
    result = guard2.check_and_update(now=1_500_000)  # rollback relative to 2_000_000
    assert not result.ok, "surviving redundant copy should still catch the rollback"


def test_corrupting_one_redundant_copy_does_not_reset_the_ratchet(tmp_path):
    p1, p2 = tmp_path / "a.json", tmp_path / "b.json"
    guard = ClockGuard([str(p1), str(p2)], machine_id="M1", tolerance_seconds=300)
    guard.check_and_update(now=5_000_000)

    # Hand-edit p1's last_seen_unix without recomputing its hmac. The
    # on-disk content is base64(json(...)), so decode, edit, re-encode.
    data = json.loads(base64.b64decode(p1.read_text()))
    data["last_seen_unix"] = 1
    p1.write_text(base64.b64encode(json.dumps(data).encode()).decode())

    guard2 = ClockGuard([str(p1), str(p2)], machine_id="M1", tolerance_seconds=300)
    result = guard2.check_and_update(now=100)
    assert not result.ok, "tampered copy must be ignored, not trusted"
    assert str(p1) in result.tampered_paths
    assert str(p2) not in result.tampered_paths


def test_state_file_is_bound_to_machine_id(tmp_path):
    path = tmp_path / "clock.json"
    ClockGuard(str(path), machine_id="MACHINE-A").check_and_update(now=9_000_000)

    # A different machine_id can't use this machine's history to detect
    # a rollback -- and, importantly, is NOT falsely flagged either: it
    # just starts its own fresh baseline.
    guard_b = ClockGuard(str(path), machine_id="MACHINE-B")
    result = guard_b.check_and_update(now=1)
    assert result.ok


# --- Layer 2: intra-session monotonic drift check ---------------------------


def _guard_with_pinned_session(tmp_path, wall0=1000.0, mono0=500.0, tolerance=300):
    guard = ClockGuard(str(tmp_path / "clock.json"), machine_id="M1", tolerance_seconds=tolerance)
    guard.start_session(now=wall0)
    guard._session_mono0 = mono0  # pin for a deterministic test
    return guard


def test_session_drift_normal_progression_is_ok(tmp_path):
    guard = _guard_with_pinned_session(tmp_path)
    with mock.patch("time.monotonic", return_value=500.0 + 60):
        result = guard.check_session_drift(now=1000 + 60)
    assert result.ok


def test_session_drift_rollback_during_session_is_detected(tmp_path):
    guard = _guard_with_pinned_session(tmp_path)
    with mock.patch("time.monotonic", return_value=500.0 + 3600):  # 1 real hour passed
        result = guard.check_session_drift(now=1000 - 500)  # wall clock reads earlier than start
    assert not result.ok
    assert result.reason == "clock_tampering"


def test_session_drift_sleep_resume_is_not_a_false_positive(tmp_path):
    """A laptop sleeping/resuming makes wall time jump far ahead while
    CLOCK_MONOTONIC barely advances. This must never be flagged."""
    guard = _guard_with_pinned_session(tmp_path)
    with mock.patch("time.monotonic", return_value=500.0 + 2):  # only 2s of monotonic elapsed
        result = guard.check_session_drift(now=1000 + 5 * 3600)  # wall jumped forward 5 hours
    assert result.ok


def test_session_drift_small_drift_within_tolerance_is_ok(tmp_path):
    guard = _guard_with_pinned_session(tmp_path, tolerance=300)
    with mock.patch("time.monotonic", return_value=500.0 + 120):
        result = guard.check_session_drift(now=1000 + 120 - 60)  # 60s lag, tolerance is 300s
    assert result.ok


def test_check_session_drift_without_start_session_bootstraps_silently(tmp_path):
    """Calling check_session_drift() before start_session() shouldn't
    crash - it should just start the session and report ok."""
    guard = ClockGuard(str(tmp_path / "clock.json"), machine_id="M1")
    result = guard.check_session_drift(now=1000)
    assert result.ok


# --- Content is obscured, not human-readable --------------------------------


def test_on_disk_content_is_not_readable_json(tmp_path):
    path = tmp_path / "state.dat"
    ClockGuard(str(path), machine_id="M1").check_and_update(now=1_000_000)
    raw = path.read_text()

    # It must NOT be parseable as JSON directly...
    with pytest.raises(json.JSONDecodeError):
        json.loads(raw)
    # ...and it must not contain any of the field names in cleartext.
    for revealing_word in ("last_seen_unix", "hmac", "clock", "license"):
        assert revealing_word not in raw

    # It IS recoverable by base64-decoding first - this is obfuscation
    # against casual inspection, not encryption; the plan is explicit
    # that this isn't meant to withstand a determined attacker.
    decoded = json.loads(base64.b64decode(raw))
    assert decoded["last_seen_unix"] == 1_000_000


# --- Explicit tamper / missing / recovery reporting -------------------------


def test_missing_copy_is_reported_and_recreated_on_next_check(tmp_path):
    p1, p2 = tmp_path / "a.dat", tmp_path / "b.dat"
    guard = ClockGuard([str(p1), str(p2)], machine_id="M1")
    guard.check_and_update(now=1_000_000)

    p1.unlink()
    assert not p1.exists()

    guard2 = ClockGuard([str(p1), str(p2)], machine_id="M1")
    result = guard2.check_and_update(now=1_000_100)

    assert result.ok
    assert str(p1) in result.missing_paths
    assert str(p1) in result.recovered_paths  # recreated during this same call
    assert p1.exists(), "missing copy should have been recreated"

    # And the recreated copy now agrees with the survivor.
    guard3 = ClockGuard([str(p1), str(p2)], machine_id="M1")
    status, value = guard3._read_one(p1)
    assert status == "valid" and value == 1_000_100


def test_tampered_copy_is_reported_separately_from_missing(tmp_path):
    p1, p2 = tmp_path / "a.dat", tmp_path / "b.dat"
    guard = ClockGuard([str(p1), str(p2)], machine_id="M1")
    guard.check_and_update(now=1_000_000)
    p1.write_text("not even base64 !!! $$$")  # garbage, not just wrong content

    guard2 = ClockGuard([str(p1), str(p2)], machine_id="M1")
    result = guard2.check_and_update(now=1_000_100)

    assert result.ok  # survivor (p2) still lets this succeed
    assert str(p1) in result.tampered_paths
    assert str(p1) not in result.missing_paths
    assert str(p1) in result.recovered_paths  # overwritten with good data


def test_single_path_still_works_but_logs_a_warning(tmp_path, caplog):
    with caplog.at_level("WARNING"):
        guard = ClockGuard(str(tmp_path / "solo.dat"), machine_id="M1")
    assert any(
        "only 1 state path" in r.message or "1 state path(s)" in r.message
        for r in caplog.records
    )
    result = guard.check_and_update(now=1_000_000)
    assert result.ok  # still fully functional, just less resilient
