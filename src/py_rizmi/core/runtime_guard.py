"""Runtime license enforcement for long-running applications.

A startup-time license check alone is not enough for processes that
stay alive for weeks (backend servers, workers, daemons): a license
that was valid on day one can expire while the process keeps serving
traffic, because nothing re-checks it. This module closes that gap.

`LicenseWatchdog` runs a daemon thread that re-validates the license
file every *interval_seconds* and reports state transitions through
callbacks:

- ``on_valid``     -- license checked OK (fired once on entering the
                      valid state, not on every poll)
- ``on_grace``     -- license expired but still inside its grace period
- ``on_violation`` -- the license must stop being honored: expired past
                      the grace period, tampered signature, HWID
                      mismatch, missing file, unsupported schema, clock
                      tampering, or any unexpected error

Intended usage in a backend::

    watchdog = LicenseWatchdog(
        validator, "license.lic",
        interval_seconds=600,
        on_violation=lambda reason, detail: server.shutdown(),
    )
    watchdog.start()

The host application decides what "stop" means (shutdown the HTTP
server, stop accepting jobs, exit) -- the watchdog never kills the
process itself, it only reports. Callbacks fire on *state changes*
only (valid -> grace -> violation), not on every poll, so a shutdown
handler is not re-invounced once per interval. A callback that raises
is logged and swallowed so it can never kill the watchdog thread.

The first check runs synchronously inside `start()`; with
*strict_start=True* an already-invalid license raises
`LicenseWatchdogError` before the background thread is created.

Threat-model note: this enforces the same signed-license trust model
as `core.license_validator`; it adds temporal enforcement (expiry
noticed while running), not new cryptographic guarantees.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional, Protocol

from py_rizmi.models.license_payload import LicensePayload

logger = logging.getLogger("license")

ViolationCallback = Callable[[str, str], None]
PayloadCallback = Callable[[LicensePayload], None]

_STATE_VALID = "valid"
_STATE_GRACE = "grace"
_STATE_VIOLATION = "violation"


class LicenseWatchdogError(RuntimeError):
    """Raised by strict-start mode when the license is already invalid."""


class _ValidatorLike(Protocol):
    """Anything shaped like `core.license_validator.LicenseValidator`."""

    def validate_from_file(
        self, license_path: str, check_hwid: bool = True
    ) -> LicensePayload: ...


class LicenseWatchdog:
    """Periodically re-validates a license file for long-running apps.

    The first check happens synchronously inside `start()` so an
    already-invalid license is reported (or raised, with
    *strict_start*) before any background thread exists.
    """

    def __init__(
        self,
        validator: _ValidatorLike,
        license_path: str,
        *,
        interval_seconds: float = 3600.0,
        check_hwid: bool = True,
        on_valid: Optional[PayloadCallback] = None,
        on_grace: Optional[PayloadCallback] = None,
        on_violation: Optional[ViolationCallback] = None,
        strict_start: bool = False,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self._validator = validator
        self._license_path = license_path
        self.interval_seconds = interval_seconds
        self.check_hwid = check_hwid
        self._on_valid = on_valid
        self._on_grace = on_grace
        self._on_violation = on_violation
        self.strict_start = strict_start

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._starting = False

        # Last observed state, exposed read-only-ish for introspection.
        self.last_payload: Optional[LicensePayload] = None
        self.last_reason: Optional[str] = None
        self._last_reported_state: Optional[str] = None

    # ---- public API -----------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Run the initial check synchronously, then start polling."""
        with self._lock:
            if self.is_running or self._starting:
                return
            self._starting = True
            self._stop_event.clear()
        try:
            # Run the first check WITHOUT holding _lock: a callback may
            # legitimately call stop(), which needs to acquire _lock.
            ok = self.check_once()
            if not ok and self.strict_start:
                reason = self.last_reason or "unknown"
                raise LicenseWatchdogError(
                    f"License check failed at startup: {reason}"
                )
            thread = threading.Thread(
                target=self._loop, name="rizmi-license-watchdog", daemon=True
            )
            with self._lock:
                if self._stop_event.is_set():
                    # stop() was called from a startup callback; honor it.
                    return
                self._thread = thread
            thread.start()
        finally:
            with self._lock:
                self._starting = False

    def stop(self, timeout: float = 5.0) -> None:
        """Stop polling. Returns once the background thread has exited."""
        self._stop_event.set()
        thread = self._thread
        # Guard against stop() being called from inside a watchdog
        # callback (joining yourself would deadlock).
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=timeout)
        with self._lock:
            self._thread = None

    def check_once(self) -> bool:
        """Run one validation cycle. Returns True if the license is honored."""
        try:
            payload = self._validator.validate_from_file(
                self._license_path, check_hwid=self.check_hwid
            )
        except ValueError as exc:
            # LicenseValidator raises ValueError whose message is an
            # ERROR_MESSAGES key ('expired', 'tampered', 'hwid_mismatch',
            # 'clock_tampering', ...).
            self._report_violation(str(exc), "")
            return False
        except Exception as exc:
            # e.g. MachineIdError from the HWID backend, unreadable file.
            logger.warning("License watchdog: unexpected error (%s)", exc)
            self._report_violation("error", str(exc))
            return False

        self.last_payload = payload
        self.last_reason = None
        if getattr(payload, "in_grace_period", False):
            self._transition(_STATE_GRACE, payload)
        else:
            self._transition(_STATE_VALID, payload)
        return True

    def __enter__(self) -> "LicenseWatchdog":
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stop()

    @classmethod
    def from_config(
        cls,
        config: Any,
        validator: _ValidatorLike,
        license_path: str,
        *,
        interval_seconds: Optional[float] = None,
        check_hwid: Optional[bool] = None,
        strict_start: Optional[bool] = None,
        on_valid: Optional[PayloadCallback] = None,
        on_grace: Optional[PayloadCallback] = None,
        on_violation: Optional[ViolationCallback] = None,
    ) -> "LicenseWatchdog":
        """Build a watchdog from a `RizmiConfig`.

        Explicit keyword arguments take precedence over config values;
        config values take precedence over library defaults. Example:
        a developer can set ``watchdog_interval_seconds=60`` (1 minute)
        or ``7200`` (2 hours) centrally and override per-instance when
        needed.
        """
        return cls(
            validator,
            license_path,
            interval_seconds=(
                interval_seconds
                if interval_seconds is not None
                else float(config.watchdog_interval_seconds)
            ),
            check_hwid=(
                check_hwid if check_hwid is not None else bool(config.check_hwid)
            ),
            strict_start=(
                strict_start
                if strict_start is not None
                else bool(config.watchdog_strict_start)
            ),
            on_valid=on_valid,
            on_grace=on_grace,
            on_violation=on_violation,
        )

    # ---- internals -------------------------------------------------------

    def _loop(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            self.check_once()

    def _transition(self, state: str, payload: LicensePayload) -> None:
        """Fire the callback for *state*, but only when the state changed."""
        if self._last_reported_state == state:
            return
        self._last_reported_state = state
        callback = self._on_valid if state == _STATE_VALID else self._on_grace
        if callback is not None:
            self._safe_call(lambda: callback(payload))

    def _report_violation(self, reason: str, detail: str) -> None:
        self.last_reason = reason
        logger.warning("License watchdog: violation (%s) %s", reason, detail)
        if self._last_reported_state == _STATE_VIOLATION:
            return
        self._last_reported_state = _STATE_VIOLATION
        on_violation = self._on_violation
        if on_violation is not None:
            self._safe_call(lambda: on_violation(reason, detail))

    @staticmethod
    def _safe_call(call: Callable[[], None]) -> None:
        try:
            call()
        except Exception:
            # A broken shutdown handler must never kill the watchdog thread.
            logger.exception("License watchdog: callback raised")
