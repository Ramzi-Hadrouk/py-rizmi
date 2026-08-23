"""Trial period management — license-free evaluation for long-running apps.

Lets a developer give a client N days of full app usage without any
license file. On first run the app issues itself a *self-signed trial
license*; when the trial ends, `check()` reports an expired state and
the host application blocks (or degrades) until the client buys a real
`license.lic`, which always supersedes the trial.

Design
------
A trial is modeled as exactly what it is: a license the app issues to
itself, using the SAME payload schema and validation machinery as real
licenses -- but signed with a LOCALLY GENERATED trial keypair instead
of the vendor's key:

- The vendor's public key is embedded in the app (existing model).
- First run: generate a trial keypair in *config_dir*, self-sign a
  trial license (``mode="trial"``, ``exp = start + trial_days``, HWID-
  bound), store as ``trial.lic``.
- Later runs: validate ``trial.lic`` against the trial public key with
  HWID binding AND ClockGuard anti-rollback -- reusing the project's
  existing tamper detection rather than inventing weaker checks.
- A REAL license validated with the vendor key always wins: clients
  can buy at any point, mid-trial or after expiry.

Tamper resistance (honest threat model)
---------------------------------------
- Editing trial.lic            -> signature failure -> state "tampered"
- Copying another machine's    -> HWID mismatch     -> state "tampered"
  trial
- Rolling back the clock to    -> ClockGuard high-water mark catches it
  extend the trial                -> state "tampered"
- Deleting trial.lic to        -> the trial's original start date is
  restart the trial               ratcheted into ClockGuard state files;
                                  a fresh trial inherits that date, so
                                  deletion does NOT reset the clock.
- Swapping in a forged trial   -> forger would need the trial private
  signed long ago                 key... which lives on THIS machine,
                                  so this reduces to editing the file
                                  (caught by signature) unless the
                                  attacker also forges ClockGuard
                                  state -- documented as out of scope,
                                  same trust level as clock_guard's own
                                  HMAC analysis.

Like every offline licensing mechanism, this raises the bar against
casual-to-moderate tampering, not a determined reverse engineer with a
debugger and full disk access.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

from py_rizmi.core.clock_guard import ClockGuard
from py_rizmi.core.crypto import generate_rsa_keypair, save_pem
from py_rizmi.core.hwid import HardwareIdentifier
from py_rizmi.core.license_issuer import LicenseIssuer
from py_rizmi.core.license_validator import ERROR_MESSAGES, LicenseValidator
from py_rizmi.models.license_payload import LicensePayload


def _decode_exp(token: str, public_key_pem: str) -> int:
    """Best-effort exp extraction from a token (signature still verified)."""
    import jwt

    try:
        data = jwt.decode(
            token, public_key_pem, algorithms=["RS256"], options={"verify_exp": False}
        )
        return int(data.get("exp", 0))
    except Exception:
        return 0

logger = logging.getLogger("license")

TRIAL_SCHEMA_VERSION = 1
TRIAL_MODE = "trial"
TRIAL_KEY_FILE = "trial_key.pem"
TRIAL_PUB_FILE = "trial_key_pub.pem"
TRIAL_LICENSE_FILE = "trial.lic"

# ClockGuard state marker recording the FIRST-EVER trial start on this
# machine. Stored via the same redundant HMAC'd state files the clock
# guard uses, so deleting trial.lic cannot restart the trial clock.
_TRIAL_START_MARKER = "py-rizmi-trial-start"


@dataclass
class TrialStatus:
    """Outcome of a trial check."""

    # One of:
    #   "licensed"      -- a real vendor license is present and valid
    #   "trial_active"  -- trial running, days_left > 0
    #   "trial_expired" -- trial period over; block or degrade
    #   "tampered"      -- trial file fails signature/HWID/clock checks
    #   "error"         -- unexpected infrastructure failure
    state: str
    days_left: int = 0
    payload: Optional[LicensePayload] = None
    detail: str = ""

    @property
    def ok(self) -> bool:
        """True if the app may run (licensed or trial still active)."""
        return self.state in ("licensed", "trial_active")


def _read_json_file(path: Path) -> Optional[str]:
    try:
        return path.read_text().strip()
    except FileNotFoundError:
        return None


class TrialManager:
    """Self-service trial periods bound to one machine.

    Parameters
    ----------
    config_dir:
        Directory where ``trial.lic`` and the trial keypair live. Use
        your app's own config directory (e.g. platformdirs user_config_dir).
    trial_days:
        Length of the trial in days. Must be positive.
    public_key:
        Vendor RSA public key (PEM string). When a real license in
        *config_dir* validates against it, the trial is irrelevant.
    license_path:
        Where clients are told to drop their purchased ``license.lic``.
        Defaults to ``<config_dir>/license.lic``.
    hwid:
        Override the machine fingerprint source (testing / custom
        providers). Defaults to `HardwareIdentifier`.
    enable_clock_guard:
        Anti-rollback protection for the trial clock. Disable only for
        diagnostics/tests.
    """

    def __init__(
        self,
        config_dir: str | Path,
        *,
        trial_days: int = 14,
        public_key: str,
        license_path: str | Path | None = None,
        hwid_provider: Any = None,
        enable_clock_guard: bool = True,
    ) -> None:
        if trial_days <= 0:
            raise ValueError("trial_days must be positive")
        if not public_key or not isinstance(public_key, str):
            raise ValueError("public_key must be a non-empty PEM string")

        self.config_dir = Path(config_dir)
        self.trial_days = trial_days
        self.public_key = public_key
        self.license_path = (
            Path(license_path) if license_path else self.config_dir / "license.lic"
        )
        self._hwid_getter = hwid_provider or HardwareIdentifier.get_machine_id
        self.enable_clock_guard = enable_clock_guard

    # ---- machine binding -------------------------------------------------

    def _hwid(self) -> str:
        return self._hwid_getter()

    def _clock_guard(self) -> ClockGuard:
        return ClockGuard(self._clock_paths(), machine_id=self._hwid())

    def set_clock_state_paths(self, paths: List[str]) -> None:
        """Override the redundant ClockGuard state locations (testing and
        integrations that want custom placement)."""
        self._custom_clock_paths = paths

    def _clock_paths(self) -> List[str]:
        if getattr(self, "_custom_clock_paths", None):
            return list(self._custom_clock_paths)
        from py_rizmi.integrations.validation import _default_state_paths

        return _default_state_paths(
            str(self.config_dir), app_name=_TRIAL_START_MARKER
        )

    # ---- trial issuance --------------------------------------------------

    def _trial_key_paths(self) -> tuple[Path, Path]:
        return (
            self.config_dir / TRIAL_KEY_FILE,
            self.config_dir / TRIAL_PUB_FILE,
        )

    def _ensure_trial_keypair(self) -> str:
        """Return the trial PUBLIC key PEM, generating the pair if needed."""
        priv_path, pub_path = self._trial_key_paths()
        if priv_path.exists() and pub_path.exists():
            pub_pem = _read_json_file(pub_path)
            if pub_pem:
                return pub_pem
        private_pem, public_pem = generate_rsa_keypair(2048)
        save_pem(private_pem, str(priv_path))
        try:
            os.chmod(priv_path, 0o600)
        except OSError:
            pass
        save_pem(public_pem, str(pub_path))
        logger.info("Trial keypair generated in %s", self.config_dir)
        return public_pem

    def issue_trial(self) -> LicensePayload:
        """Create (or re-create) the self-signed trial license.

        The trial START DATE is inherited from the ClockGuard ratchet if
        this machine has run a trial before -- deleting trial.lic does
        not reset the clock.
        """
        self.config_dir.mkdir(parents=True, exist_ok=True)
        trial_pub = self._ensure_trial_keypair()

        now = int(time.time())
        start = self._ratchet_trial_start(now)

        payload = LicensePayload(
            schema_version=TRIAL_SCHEMA_VERSION,
            client="(trial)",
            license_id=f"trial-{self._hwid()[:12]}",
            hwid=self._hwid(),
            features=[],
            max_clients=1,
            mode=TRIAL_MODE,
            grace_days=0,
            iat=start,
            exp=start + self.trial_days * 86_400,
        )
        issuer = LicenseIssuer.from_file(
            str(self.config_dir / TRIAL_KEY_FILE)
        )
        token = issuer.issue(payload)
        (self.config_dir / TRIAL_LICENSE_FILE).write_text(token)
        logger.info(
            "Trial license issued: start=%d exp=%d (%d days)",
            start, payload.exp, self.trial_days,
        )
        # Reference kept explicit: trial_pub is what validation will load.
        assert trial_pub
        return payload

    def _ratchet_trial_start(self, now: int) -> int:
        """Record/inherit the first-ever trial start via ClockGuard state.

        Returns the effective trial start timestamp. If state files show
        an earlier trial ever existed on this machine, that earlier date
        is used -- deleting trial.lic cannot restart the trial.
        """
        if not self.enable_clock_guard:
            return now
        guard = self._clock_guard()
        result = guard.check_and_update(float(now))
        if not result.ok:
            # Clock reads BEFORE a previously recorded high-water mark --
            # rollback attempt during (re)issuance. Do not reward it: use
            # the recorded mark as the start.
            logger.warning("Trial issuance: clock rollback detected (%s)", result.detail)
            return result.last_seen_unix
        return result.last_seen_unix

    # ---- checking ---------------------------------------------------------

    def check(self) -> TrialStatus:
        """Full status resolution: real license first, then trial."""
        # 1. Real license always supersedes the trial.
        licensed = self._check_real_license()
        if licensed is not None:
            return licensed

        # 2. No real license -> evaluate the trial.
        return self._check_trial()

    def start_or_check(self) -> TrialStatus:
        """Convenience for app startup: create the trial on first run."""
        status = self.check()
        if status.state == "no_trial":
            self.issue_trial()
            status = self.check()
        return status

    def _check_real_license(self) -> Optional[TrialStatus]:
        token = _read_json_file(self.license_path)
        if token is None:
            return None
        validator = LicenseValidator(self.public_key)
        custom_hwid = not isinstance(
            self._hwid_getter, type(HardwareIdentifier.get_machine_id)
        )
        try:
            payload = validator.validate(token, check_hwid=not custom_hwid)
            if custom_hwid and payload.hwid.lower() != self._hwid().lower():
                raise ValueError("hwid_mismatch")
        except ValueError as exc:
            reason = str(exc)
            detail = ERROR_MESSAGES.get(reason, reason)
            # A corrupt/expired REAL license must not silently fall back
            # to trial: the client owns a license; surface the problem.
            return TrialStatus(
                state="licensed_invalid",
                payload=None,
                detail=detail,
            )
        return TrialStatus(state="licensed", days_left=max(0, (payload.exp - int(time.time())) // 86_400), payload=payload)

    def _check_trial(self) -> TrialStatus:
        trial_lic = self.config_dir / TRIAL_LICENSE_FILE
        token = _read_json_file(trial_lic)
        if token is None:
            return TrialStatus(state="no_trial", detail="No trial has been started.")

        _, trial_pub_path = self._trial_key_paths()
        trial_pub = _read_json_file(trial_pub_path)
        if trial_pub is None:
            return TrialStatus(
                state="tampered",
                detail="Trial key material missing.",
            )

        clock_guard = self._clock_guard() if self.enable_clock_guard else None
        validator = LicenseValidator(trial_pub, clock_guard=clock_guard)
        # When a custom HWID provider is injected, LicenseValidator cannot
        # do the machine comparison itself (it uses the real HardwareIden-
        # tifier); skip its check and compare against our provider instead.
        custom_hwid = not isinstance(self._hwid_getter, type(HardwareIdentifier.get_machine_id))
        try:
            payload = validator.validate(token, check_hwid=not custom_hwid)
        except ValueError as exc:
            reason = str(exc)
            if reason == "expired":
                exp = _decode_exp(token, trial_pub)
                days_over = max(0, (int(time.time()) - exp) // 86_400)
                return TrialStatus(
                    state="trial_expired",
                    days_left=0,
                    detail=f"Trial ended {days_over} day(s) ago.",
                )
            detail = ERROR_MESSAGES.get(reason, reason)
            logger.warning("Trial check failed: %s (%s)", reason, detail)
            return TrialStatus(state="tampered", detail=detail)
        except Exception as exc:
            return TrialStatus(state="error", detail=str(exc))

        if payload.mode != TRIAL_MODE:
            return TrialStatus(
                state="tampered",
                detail="Trial file is not a trial-mode license.",
            )

        if custom_hwid and payload.hwid.lower() != self._hwid().lower():
            logger.warning("Trial check failed: hwid_mismatch (custom provider)")
            return TrialStatus(state="tampered", detail="Hardware fingerprint mismatch.")

        seconds_left = payload.exp - int(time.time())
        days_left = max(0, (seconds_left + 86_399) // 86_400)  # ceil
        return TrialStatus(
            state="trial_active",
            days_left=int(days_left),
            payload=payload,
        )
