"""Tests for core.runtime_guard.LicenseWatchdog (runtime license enforcement).

Covers the feature requested in the audit: a long-running app (backend
server) must stop honoring a license the moment it expires -- without
restarting the process.
"""
from __future__ import annotations

import threading
import time
from typing import Any, List, Tuple

import pytest

from py_rizmi.core.runtime_guard import (
    LicenseWatchdog,
    LicenseWatchdogError,
)
from py_rizmi.models.license_payload import LicensePayload


def _payload(in_grace: bool = False) -> LicensePayload:
    p = LicensePayload(client="acme", license_id="L-1")
    p.in_grace_period = in_grace
    return p


class FakeValidator:
    """Scriptable stand-in for LicenseValidator.

    Results are consumed in order; a result that is an Exception
    instance is raised, anything else is returned.
    """

    def __init__(self, results: List[Any] | None = None) -> None:
        self.results = list(results or [])
        self.calls: List[Tuple[str, bool]] = []
        self.lock = threading.Lock()

    def validate_from_file(self, license_path: str, check_hwid: bool = True):
        with self.lock:
            self.calls.append((license_path, check_hwid))
            result = self.results.pop(0) if self.results else _payload()
        if isinstance(result, Exception):
            raise result
        return result


class TestCheckOnce:
    def test_valid_license_returns_true_and_fires_on_valid_once(self):
        fired = []
        wd = LicenseWatchdog(
            FakeValidator(), "license.lic", on_valid=fired.append
        )
        assert wd.check_once() is True
        assert len(fired) == 1
        assert fired[0].client == "acme"
        # Same state on the next poll must NOT re-fire (no callback spam).
        wd.check_once()
        assert len(fired) == 1

    def test_grace_period_reports_grace_not_violation(self):
        graces, violations = [], []
        wd = LicenseWatchdog(
            FakeValidator([_payload(in_grace=True)]),
            "license.lic",
            on_grace=graces.append,
            on_violation=lambda r, d: violations.append((r, d)),
        )
        assert wd.check_once() is True
        assert len(graces) == 1
        assert violations == []
        assert wd.last_reason is None

    def test_grace_to_violation_transition(self):
        violations, graces = [], []
        wd = LicenseWatchdog(
            FakeValidator([_payload(in_grace=True), ValueError("expired")]),
            "license.lic",
            on_grace=graces.append,
            on_violation=lambda r, d: violations.append((r, d)),
        )
        assert wd.check_once() is True
        assert wd.check_once() is False
        assert violations == [("expired", "")]
        assert len(graces) == 1  # grace fired exactly once in the lifecycle

    @pytest.mark.parametrize(
        "reason", ["expired", "tampered", "hwid_mismatch", "missing",
                   "clock_tampering", "unsupported_schema", "decode_error"]
    )
    def test_every_validator_error_reason_reaches_on_violation(self, reason):
        violations = []
        wd = LicenseWatchdog(
            FakeValidator([ValueError(reason)]),
            "license.lic",
            on_violation=lambda r, d: violations.append(r),
        )
        assert wd.check_once() is False
        assert violations == [reason]
        assert wd.last_reason == reason

    def test_unexpected_exception_maps_to_error_reason(self):
        violations = []
        wd = LicenseWatchdog(
            FakeValidator([RuntimeError("disk exploded")]),
            "license.lic",
            on_violation=lambda r, d: violations.append((r, d)),
        )
        assert wd.check_once() is False
        assert violations == [("error", "disk exploded")]

    def test_violation_fires_only_once_across_repeated_failures(self):
        violations = []
        wd = LicenseWatchdog(
            FakeValidator([ValueError("expired")] * 5),
            "license.lic",
            on_violation=lambda r, d: violations.append(r),
        )
        for _ in range(5):
            wd.check_once()
        assert violations == ["expired"]

    def test_recovery_after_violation_re_reports_valid(self):
        """If the license becomes valid again (e.g. file replaced), the
        valid callback fires again after a violation state."""
        events = []
        wd = LicenseWatchdog(
            FakeValidator([
                ValueError("expired"),
                _payload(),
            ]),
            "license.lic",
            on_valid=lambda p: events.append("valid"),
            on_violation=lambda r, d: events.append(("violation", r)),
        )
        wd.check_once()
        wd.check_once()
        assert events == [("violation", "expired"), "valid"]

    def test_check_hwid_flag_is_passed_through(self):
        validator = FakeValidator()
        wd = LicenseWatchdog(validator, "license.lic", check_hwid=False)
        wd.check_once()
        assert validator.calls == [("license.lic", False)]


class TestStartStop:
    def test_strict_start_raises_on_invalid_license(self):
        wd = LicenseWatchdog(
            FakeValidator([ValueError("expired")]),
            "license.lic",
            strict_start=True,
        )
        with pytest.raises(LicenseWatchdogError, match="expired"):
            wd.start()
        # No background thread may exist after a failed strict start.
        assert wd.is_running is False

    def test_strict_start_success_runs_background(self):
        wd = LicenseWatchdog(FakeValidator(), "license.lic", strict_start=True)
        wd.start()
        try:
            assert wd.is_running is True
        finally:
            wd.stop()
        assert wd.is_running is False

    def test_non_strict_start_with_invalid_license_still_polls(self):
        violations = []
        wd = LicenseWatchdog(
            FakeValidator([ValueError("missing")]),
            "license.lic",
            on_violation=lambda r, d: violations.append(r),
        )
        wd.start()  # no raise: default strict_start=False
        try:
            assert wd.is_running is True
            assert violations == ["missing"]
        finally:
            wd.stop()

    def test_double_start_is_noop(self):
        wd = LicenseWatchdog(FakeValidator(), "license.lic")
        wd.start()
        try:
            thread_first = wd._thread
            wd.start()
            assert wd._thread is thread_first
        finally:
            wd.stop()

    def test_stop_is_idempotent_and_joinable(self):
        wd = LicenseWatchdog(FakeValidator(), "license.lic")
        wd.start()
        wd.stop()
        wd.stop()
        assert wd.is_running is False

    def test_stop_from_inside_callback_does_not_deadlock(self):
        """A violation handler that calls stop() must not hang."""
        wd = LicenseWatchdog(
            FakeValidator([ValueError("expired")]),
            "license.lic",
            on_violation=lambda r, d: wd.stop(),
        )
        wd.start()
        # If stop() deadlocked when called from the watchdog thread, the
        # watchdog thread would still be alive waiting on itself.
        deadline = time.monotonic() + 5
        while wd.is_running and time.monotonic() < deadline:
            time.sleep(0.01)
        assert wd.is_running is False

    def test_context_manager(self):
        with LicenseWatchdog(FakeValidator(), "license.lic") as wd:
            assert wd.is_running is True
        assert wd.is_running is False

    def test_invalid_interval_rejected(self):
        with pytest.raises(ValueError, match="interval_seconds"):
            LicenseWatchdog(FakeValidator(), "license.lic", interval_seconds=0)
        with pytest.raises(ValueError, match="interval_seconds"):
            LicenseWatchdog(FakeValidator(), "license.lic", interval_seconds=-1)


class TestBackgroundLoop:
    """Real-threading tests with short intervals."""

    def test_background_poll_detects_expiry_while_running(self):
        """THE core scenario: app starts with a valid license, the license
        expires while the process keeps running, the watchdog notices and
        fires on_violation without any restart."""
        validator = FakeValidator([_payload()])  # first check: valid
        violations = []
        started = threading.Event()

        wd = LicenseWatchdog(
            validator,
            "license.lic",
            interval_seconds=0.05,
            on_valid=lambda p: started.set(),
            on_violation=lambda r, d: violations.append(r),
        )
        wd.start()
        try:
            assert started.wait(timeout=5), "initial valid check never ran"
            # Now the license expires "while the app is running".
            with validator.lock:
                validator.results.append(ValueError("expired"))
            deadline = time.monotonic() + 5
            while not violations and time.monotonic() < deadline:
                time.sleep(0.01)
            assert violations == ["expired"], (
                "watchdog failed to notice expiry while the app was running"
            )
        finally:
            wd.stop()

    def test_background_poll_repeats(self):
        validator = FakeValidator()
        wd = LicenseWatchdog(validator, "license.lic", interval_seconds=0.02)
        wd.start()
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                with validator.lock:
                    if len(validator.calls) >= 3:
                        break
                time.sleep(0.01)
            with validator.lock:
                assert len(validator.calls) >= 3, "watchdog stopped polling"
        finally:
            wd.stop()

    def test_stop_terminates_promptly(self):
        wd = LicenseWatchdog(FakeValidator(), "license.lic", interval_seconds=60)
        t0 = time.monotonic()
        wd.start()
        wd.stop(timeout=2)
        assert time.monotonic() - t0 < 2, "stop() did not return promptly"
        assert wd.is_running is False

    def test_daemon_thread_does_not_block_interpreter_exit(self):
        wd = LicenseWatchdog(FakeValidator(), "license.lic", interval_seconds=60)
        wd.start()
        assert wd._thread is not None
        assert wd._thread.daemon is True
        wd.stop()


class TestCallbackContract:
    def test_raising_callback_does_not_kill_watchdog(self):
        def bad_callback(*a: Any) -> None:
            raise RuntimeError("shutdown handler bug")

        validator = FakeValidator([_payload(), ValueError("expired"), _payload()])
        wd = LicenseWatchdog(
            validator,
            "license.lic",
            on_valid=bad_callback,
            on_violation=bad_callback,
        )
        # All three cycles run; the watchdog survives the broken callbacks.
        assert wd.check_once() is True
        assert wd.check_once() is False
        assert wd.check_once() is True

    def test_callbacks_receive_payload_and_reason(self):
        seen = {}
        wd = LicenseWatchdog(
            FakeValidator([_payload(in_grace=True)]),
            "license.lic",
            on_grace=lambda p: seen.setdefault("grace_client", p.client),
        )
        wd.check_once()
        assert seen["grace_client"] == "acme"

    def test_no_callbacks_configured_is_fine(self):
        wd = LicenseWatchdog(FakeValidator([ValueError("expired")]), "license.lic")
        assert wd.check_once() is False  # no crash without callbacks
        assert wd.last_reason == "expired"


class TestRealValidatorIntegration:
    """End-to-end with a real LicenseValidator, keys, and license files."""

    def test_expiry_detected_across_real_files(self, tmp_path, sample_payload):
        from py_rizmi.core.keypair import KeyPairManager
        from py_rizmi.core.license_issuer import LicenseIssuer
        from py_rizmi.core.license_validator import LicenseValidator

        priv = tmp_path / "priv.pem"
        pub = tmp_path / "pub.pem"
        KeyPairManager.save_keypair(str(priv), str(pub))
        pub_pem = pub.read_text()

        lic_path = tmp_path / "license.lic"

        def write_license(exp_days: int) -> None:
            payload = LicensePayload.from_dict(sample_payload.to_dict())
            payload.set_auto_iat()
            if exp_days < 0:
                # Expire beyond the grace window so the validator raises
                # instead of reporting in_grace_period.
                payload.exp = int(time.time()) - 20 * 86_400  # 20 days ago
            else:
                payload.set_auto_exp(exp_days)
            lic_path.write_text(LicenseIssuer.from_file(str(priv)).issue(payload))

        # Day one: valid 365-day license.
        write_license(365)
        validator = LicenseValidator(pub_pem)
        violations: List[str] = []
        valid_seen = threading.Event()

        wd = LicenseWatchdog(
            validator,
            str(lic_path),
            interval_seconds=0.05,
            on_valid=lambda p: valid_seen.set(),
            on_violation=lambda r, d: violations.append(r),
            check_hwid=False,
        )
        wd.start()
        try:
            assert valid_seen.wait(timeout=5)
            # The license expires while the app keeps running.
            write_license(-1)
            deadline = time.monotonic() + 5
            while not violations and time.monotonic() < deadline:
                time.sleep(0.01)
            assert violations == ["expired"]
        finally:
            wd.stop()
