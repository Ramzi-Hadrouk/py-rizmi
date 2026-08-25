"""LicenseGate — the one-object integration facade.

Composition of audited primitives ONLY: this module adds no trust
decisions, no crypto, no storage logic. It wires StateStore +
LicenseActivator + TrialManager (+ optional keypin) so a developer's
entire integration is::

    gate = LicenseGate(app_name="MyProduct", public_key=KEY,
                       config_dir=cfg, expected_fingerprint=FP)
    status = gate.start()          # first run: starts trial
    if not status:
        show(status.message)       # blocked: expired / tampered / ...

All methods return :class:`LicenseStatus` (truthy = app may run).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Optional, Union

from py_rizmi.core.hwid import HardwareIdentifier
from py_rizmi.core.license_activator import (
    ActivationResult,
    LicenseActivator,
    LicenseStatus,
)
from py_rizmi.core.state_store import StateStore
from py_rizmi.core.trial import TrialManager

logger = logging.getLogger("license")


class _GateValidatorAdapter:
    """Adapts LicenseActivator to the LicenseWatchdog validator protocol.

    The watchdog calls ``validate_from_file(path)``; we instead
    re-validate the store's active license token directly.
    """

    def __init__(self, activator: LicenseActivator) -> None:
        self._activator = activator

    def validate_from_file(self, license_path: str, check_hwid: bool = True):  # type: ignore[no-untyped-def]
        payload, reason = self._activator.current_or_reason()
        if payload is None:
            raise ValueError(reason or "missing")
        return payload


def _gate_status_summary(gate: "LicenseGate") -> dict[str, object]:
    return gate.check().to_dict()


class LicenseGate:
    """Single entry point for licensing an application.

    Parameters
    ----------
    app_name:
        Your product name (required, must not be the toolkit default).
    public_key:
        Embedded vendor public key PEM.
    config_dir:
        Directory for the legacy license.lic fallback file.
    db_path:
        Optional explicit StateStore path; default is the per-app
        platformdirs location.
    trial_days:
        Trial length (default 14).
    expected_fingerprint:
        Optional SHA-256 hex of *public_key*; when provided,
        ``pin_fingerprint`` is enforced at construction (startup gate).
    check_hwid:
        Enforce HWID binding (default True).
    hwid_provider:
        Optional fingerprint override (testing/custom providers).
    """

    def __init__(
        self,
        *,
        app_name: str,
        public_key: str,
        config_dir: Union[str, Path],
        db_path: Optional[Union[str, Path]] = None,
        trial_days: int = 14,
        expected_fingerprint: Optional[str] = None,
        check_hwid: bool = True,
        hwid_provider: Optional[Callable[[], str]] = None,
        enable_clock_guard: bool = True,
        enable_watchdog: bool = False,
        interval_seconds: int = 600,
        on_violation: Optional[Callable[[str, str], None]] = None,
        on_valid: Optional[Callable[[Any], None]] = None,
    ) -> None:
        if not app_name or not isinstance(app_name, str):
            raise ValueError("app_name must be a non-empty string")
        if not public_key or not isinstance(public_key, str):
            raise ValueError("public_key must be a non-empty PEM string")

        if expected_fingerprint is not None:
            from py_rizmi.core.keypin import pin_fingerprint

            pin_fingerprint(public_key, expected_fingerprint)

        machine_id = (hwid_provider or HardwareIdentifier.get_machine_id)()
        self.app_name = app_name
        self.public_key = public_key

        resolved_db = Path(db_path) if db_path else StateStore.default_path(app_name)
        self.store = StateStore(
            resolved_db, machine_id=machine_id, app_name=app_name
        )
        self.activator = LicenseActivator(
            self.store,
            public_key,
            check_hwid=check_hwid,
            hwid_provider=hwid_provider,
        )
        self._trial = TrialManager(
            config_dir,
            trial_days=trial_days,
            public_key=public_key,
            use_sqlite=True,
            db_path=self.store.db_path,
            app_name=app_name,
            allow_default_namespace=True,  # already enforced above
            clock_fallback_file=self.store.db_path.parent / "clock.dat",
            check_hwid=check_hwid,
            hwid_provider=hwid_provider,
            enable_clock_guard=enable_clock_guard,
        )

        # ── optional runtime watchdog ─────────────────────────────────
        self._watchdog: Any = None
        if enable_watchdog:
            from py_rizmi.core.runtime_guard import LicenseWatchdog

            self._watchdog = LicenseWatchdog(
                _GateValidatorAdapter(self.activator),
                str(resolved_db) + "::active",  # sentinel path; adapter reads store
                interval_seconds=interval_seconds,
                on_violation=on_violation or (lambda reason, detail: None),
                on_valid=on_valid,
                strict_start=False,
            )

    # ── lifecycle ─────────────────────────────────────────────────────

    def start(self) -> LicenseStatus:
        """Call once at app startup: creates the trial on first run and
        returns the current status."""
        return self._trial_status(self._trial.start_or_check())

    def check(self) -> LicenseStatus:
        """Current state without side effects (real license → trial)."""
        # 1. A real license ALWAYS outranks the trial — including a
        #    tampered one, which must surface as licensed_invalid and
        #    never silently fall back to the trial (D10).
        raw = self.store.active_license_unverified()
        if raw is not None:
            payload, reason = self.activator.current_or_reason()
            if payload is not None:
                return LicenseStatus.from_activation(
                    ActivationResult(ok=True, payload=payload)
                )
            return LicenseStatus(
                state="licensed_invalid",
                ok=False,
                reason=reason,
                message=f"License invalid: {reason}",
            )
        # 2. No real license → trial / missing.
        trial_status = self._trial.check()
        if trial_status.state == "licensed":
            return self._licensed_status(trial_status)
        return LicenseStatus(
            state=trial_status.state,
            ok=trial_status.ok,
            days_left=trial_status.days_left,
            client=trial_status.payload.client if trial_status.payload else "",
            expires_at=trial_status.payload.exp if trial_status.payload else 0,
            message=trial_status.detail or f"{trial_status.state}",
        )

    # ── activation ────────────────────────────────────────────────────

    def activate_token(self, text: str) -> LicenseStatus:
        result = self.activator.activate_token(text)
        return LicenseStatus.from_activation(result)

    def activate_file(self, path: Union[str, Path]) -> LicenseStatus:
        result = self.activator.activate_file(path)
        return LicenseStatus.from_activation(result)

    def deactivate(self) -> None:
        self.activator.deactivate()

    def status_summary(self) -> dict[str, object]:
        """JSON-serializable current state (for UIs / support tickets)."""
        return self.check().to_dict()

    def recheck_now(self) -> None:
        """Run one watchdog poll synchronously (tests + on-demand checks)."""
        if self._watchdog is not None:
            self._watchdog.check_once()

    def start_watchdog(self) -> None:
        """Begin background re-validation (long-running apps)."""
        if self._watchdog is not None:
            self._watchdog.start()

    # ── helpers ───────────────────────────────────────────────────────

    def _trial_status(self, ts: Any) -> LicenseStatus:
        from py_rizmi.models.license_payload import LicensePayload  # noqa: F401

        if ts.state == "licensed" and ts.payload is not None:
            return self._licensed_status(ts)
        return LicenseStatus(
            state=ts.state,
            ok=ts.ok,
            days_left=ts.days_left,
            client=ts.payload.client if ts.payload else "",
            expires_at=ts.payload.exp if ts.payload else 0,
            message=ts.detail or ts.state.replace("_", " "),
        )

    def _licensed_status(self, ts: Any) -> LicenseStatus:
        assert ts.payload is not None
        return LicenseStatus.from_activation(
            ActivationResult(ok=True, payload=ts.payload)
        )
