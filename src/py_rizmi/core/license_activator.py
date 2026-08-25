"""License activation — the in-app "enter a new license" flow.

Two entry methods for end users, hosted by the DEVELOPER'S OWN UI
(py-rizmi ships no GUI dependency into your app):

- **Method A — paste:** the user pastes the license token string into
  your text field; call ``activate_token(text)``.
- **Method B — file:** the user picks their ``license.lic`` file; call
  ``activate_file(path)``.

Both run the FULL validation chain (signature against the embedded
vendor key, expiry/grace, HWID binding, optional revocation list and
ClockGuard) BEFORE anything is written to the store. Only a fully valid
license is accepted. There is no separate, weaker "accept" code path —
activation IS validation.

``current()`` re-validates on every read, so a row tampered after
activation is still caught.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Union

from py_rizmi.core.hwid import HardwareIdentifier
from py_rizmi.core.license_validator import ERROR_MESSAGES, LicenseValidator
from py_rizmi.core.state_store import StateStore
from py_rizmi.models.license_payload import LicensePayload

logger = logging.getLogger("license")

_ACTIVE_SLOT = "active"


@dataclass
class ActivationResult:
    """Outcome of an activation attempt."""

    ok: bool
    reason: str = ""
    detail: str = ""
    payload: Optional[LicensePayload] = None


@dataclass
class LicenseStatus:
    """Developer-facing license/trial state summary.

    Truthy when the app may run (licensed or active trial). ``message``
    is a ready-to-display sentence; ``to_dict()`` is JSON-safe for UIs.
    """

    state: str  # licensed | licensed_invalid | trial_active | trial_expired |
                # tampered | missing | error
    ok: bool = False
    days_left: int = 0
    client: str = ""
    expires_at: int = 0  # unix ts, 0 = n/a
    reason: str = ""
    message: str = ""

    def __post_init__(self) -> None:
        if not self.message:
            from py_rizmi.core.license_validator import ERROR_MESSAGES

            self.message = ERROR_MESSAGES.get(self.reason, self.state.replace("_", " "))

    def __bool__(self) -> bool:
        return self.ok

    @classmethod
    def from_activation(
        cls, result: ActivationResult, *, days_left: int = 0
    ) -> "LicenseStatus":
        import time

        from py_rizmi.core.license_validator import ERROR_MESSAGES

        if result.ok and result.payload is not None:
            payload = result.payload
            remaining = max(0, (payload.exp - int(time.time())) // 86_400)
            return cls(
                state="licensed",
                ok=True,
                days_left=remaining,
                client=payload.client,
                expires_at=payload.exp,
                message=f"Licensed to {payload.client} ({remaining} day(s) left)",
            )
        if result.ok:
            return cls(state="licensed", ok=True, days_left=days_left,
                       message="Licensed")
        detail = ERROR_MESSAGES.get(result.reason, result.detail or result.reason)
        return cls(
            state=result.reason or "error",
            ok=False,
            reason=result.reason,
            message=detail,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "ok": self.ok,
            "days_left": self.days_left,
            "client": self.client,
            "expires_at": self.expires_at,
            "reason": self.reason,
            "message": self.message,
        }


class LicenseActivator:
    """Validate-and-store licenses against the embedded vendor public key.

    Parameters
    ----------
    store:
        The app's namespaced :class:`StateStore`.
    public_key:
        The VENDOR RSA public key PEM — embedded in app source, never
        loaded from writable storage.
    check_hwid:
        Enforce HWID binding (default True).
    hwid_provider:
        Override the fingerprint source (testing / custom providers).
    clock_guard:
        Optional ClockGuard instance consulted during validation.
    revocation_list:
        Optional signed CRL envelope.
    """

    def __init__(
        self,
        store: StateStore,
        public_key: str,
        *,
        check_hwid: bool = True,
        hwid_provider: Optional[Callable[[], str]] = None,
        clock_guard: Any = None,
        revocation_list: Any = None,
    ) -> None:
        self.store = store
        self.public_key = public_key
        self.check_hwid = check_hwid
        self._hwid_getter = hwid_provider or HardwareIdentifier.get_machine_id
        self._clock_guard = clock_guard
        self._revocation_list = revocation_list

    # ── validation core ───────────────────────────────────────────────

    def _make_validator(self) -> LicenseValidator:
        validator = LicenseValidator(
            self.public_key,
            clock_guard=self._clock_guard,
            revocation_list=self._revocation_list,
        )
        return validator

    def _validate(self, token: str) -> LicensePayload:
        validator = self._make_validator()
        custom_hwid = self._hwid_getter is not HardwareIdentifier.get_machine_id
        payload = validator.validate(token, check_hwid=self.check_hwid and not custom_hwid)
        if self.check_hwid and custom_hwid:
            if payload.hwid.lower() != self._hwid_getter().lower():
                raise ValueError("hwid_mismatch")
        return payload

    @staticmethod
    def _failure(exc: Exception) -> ActivationResult:
        reason = str(exc)
        detail = ERROR_MESSAGES.get(reason, reason)
        logger.warning("Activation failed: %s (%s)", reason, detail)
        return ActivationResult(ok=False, reason=reason, detail=detail)

    # ── entry methods ────────────────────────────────────────────────

    def activate_token(self, text: str) -> ActivationResult:
        """Method A: validate a pasted license token; store only if valid."""
        token = (text or "").strip()
        if not token:
            return ActivationResult(ok=False, reason="missing", detail=ERROR_MESSAGES["missing"])
        try:
            payload = self._validate(token)
        except ValueError as exc:
            return self._failure(exc)
        stored = self.store.put_license(token, license_id=payload.license_id)
        logger.info(
            "License %s activated at %d", stored.license_id, stored.activated_at
        )
        return ActivationResult(ok=True, payload=payload)

    def activate_file(self, path: Union[str, Path]) -> ActivationResult:
        """Method B: validate a ``license.lic`` file; store only if valid."""
        try:
            token = Path(path).read_text().strip()
        except OSError as exc:
            return ActivationResult(
                ok=False, reason="missing", detail=f"Cannot read {path}: {exc}"
            )
        return self.activate_token(token)

    # ── reading / removing ────────────────────────────────────────────

    def current(self) -> Optional[LicensePayload]:
        """Return the active license AFTER full re-validation, else None.

        A row tampered after activation fails here — storage never
        becomes a source of trust.
        """
        active = self.store.active_license()
        if active is None:
            return None
        try:
            return self._validate(active.token)
        except ValueError as exc:
            logger.warning("Active license failed re-validation: %s", exc)
            return None

    def current_or_reason(self) -> tuple[Optional[LicensePayload], str]:
        """Like :meth:`current` but also returns the canonical failure
        reason ('' when valid) so UIs can show precise messages."""
        active = self.store.active_license()
        if active is None:
            return None, "missing"
        try:
            return self._validate(active.token), ""
        except ValueError as exc:
            reason = str(exc)
            return None, reason

    def deactivate(self) -> None:
        """Archive the currently active license (no deletion of history)."""
        with self.store._connect() as conn:
            conn.execute(
                "UPDATE licenses SET slot='archived' WHERE slot=?", [_ACTIVE_SLOT]
            )
