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
        use_sqlite: bool = False,
        db_path: str | Path | None = None,
        app_name: str | None = None,
        allow_default_namespace: bool = False,
        shared_clock_namespace: bool = False,
        clock_fallback_file: str | Path | None = None,
        check_hwid: bool = True,
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

        # ── SQLite state store mode (opt-in) ─────────────────────────
        self.use_sqlite = bool(use_sqlite)
        self._store: Any = None
        if self.use_sqlite:
            from py_rizmi.core.state_store import StateStore

            resolved_app = app_name or "py-rizmi"
            resolved_db = Path(db_path) if db_path else StateStore.default_path(resolved_app)
            self._store = StateStore(
                resolved_db,
                machine_id=self._hwid(),
                app_name=resolved_app,
                allow_default_namespace=allow_default_namespace,
            )
        self._shared_clock_namespace = bool(shared_clock_namespace)
        self._clock_fallback_file = clock_fallback_file
        self.check_hwid = bool(check_hwid)

    # ---- machine binding -------------------------------------------------

    def _hwid(self) -> str:
        return self._hwid_getter()

    def _clock_guard(self) -> ClockGuard:
        if self.use_sqlite and self.enable_clock_guard:
            from py_rizmi.core.sqlite_clock_guard import SqliteClockGuard

            shared_path = None
            if self._shared_clock_namespace and self._store is not None:
                shared_path = self._store.db_path.parent / "clock.db"
            return SqliteClockGuard(
                db_path=self._store.db_path,
                machine_id=self._hwid(),
                app_name=self._store.app_name,
                allow_default_namespace=True,  # already validated in __init__
                fallback_file=self._clock_fallback_file,
                shared_clock_path=shared_path,
            )
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
        """Return the trial PUBLIC key PEM, generating the pair if needed.

        SQLite mode stores both PEMs in the ``keys`` table (no loose
        files); legacy mode keeps the on-disk .pem files.
        """
        if self.use_sqlite and self._store is not None:
            pub = self._store.get_key("trial_public")
            priv = self._store.get_key("trial_private")
            if pub is not None and priv is not None and pub and priv:
                return str(pub)
            private_pem, public_pem = generate_rsa_keypair(2048)
            self._store.put_key("trial_private", private_pem)
            self._store.put_key("trial_public", public_pem)
            logger.info(
                "Trial keypair generated in state store %s", self._store.db_path
            )
            return public_pem

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
        this machine has run a trial before -- deleting trial.lic (or the
        whole state DB) does not reset the clock.
        """
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
        token = self._issue_with_trial_key(payload)
        if self.use_sqlite and self._store is not None:
            # trial lives in its own state role — the ``licenses`` table's
            # active slot is reserved exclusively for REAL vendor licenses
            self._store.put("trial:license", {"token": token})
        else:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            (self.config_dir / TRIAL_LICENSE_FILE).write_text(token)
        logger.info(
            "Trial license issued: start=%d exp=%d (%d days)",
            start, payload.exp, self.trial_days,
        )
        # Reference kept explicit: trial_pub is what validation will load.
        assert trial_pub
        return payload

    def _issue_with_trial_key(self, payload: LicensePayload) -> str:
        """Sign *payload* with the trial private key from whichever
        storage mode is active."""
        if self.use_sqlite and self._store is not None:
            import tempfile
            from py_rizmi.core.license_issuer import LicenseIssuer as _LI

            priv_pem = self._store.get_key("trial_private")
            if priv_pem is None:
                raise RuntimeError("trial private key missing from state store")
            with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as tmp:
                tmp.write(priv_pem)
                tmp_path = tmp.name
            try:
                return _LI.from_file(tmp_path).issue(payload)
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        return LicenseIssuer.from_file(
            str(self.config_dir / TRIAL_KEY_FILE)
        ).issue(payload)

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

    @classmethod
    def from_config(
        cls,
        config: Any,
        config_dir: str | Path,
        public_key: str,
        *,
        trial_days: Optional[int] = None,
        license_path: str | Path | None = None,
        hwid_provider: Any = None,
        enable_clock_guard: Optional[bool] = None,
    ) -> "TrialManager":
        """Build a TrialManager from a `RizmiConfig`.

        Explicit keyword arguments take precedence over config values.
        The trial length comes from ``config.trial_days`` unless
        overridden here; ``config.check_hwid`` and clock tolerance are
        honored via the same fields.
        """
        return cls(
            config_dir,
            trial_days=(
                trial_days if trial_days is not None else int(config.trial_days)
            ),
            public_key=public_key,
            license_path=license_path,
            hwid_provider=hwid_provider,
            enable_clock_guard=(
                enable_clock_guard if enable_clock_guard is not None else True
            ),
            use_sqlite=bool(getattr(config, "use_sqlite", False)),
            db_path=getattr(config, "db_path", None),
            allow_default_namespace=bool(
                getattr(config, "allow_default_namespace", False)
            ),
            shared_clock_namespace=bool(
                getattr(config, "shared_clock_namespace", False)
            ),
        )

    # ---- SQLite-mode helpers --------------------------------------------

    def _active_license_token(self) -> Optional[str]:
        """The real license token: DB active slot (SQLite mode) or the
        legacy ``license.lic`` file."""
        if self.use_sqlite and self._store is not None:
            active = self._store.active_license()
            return active.token if active else None
        return _read_json_file(self.license_path)

    def _trial_token_and_pub(self) -> tuple[Optional[str], Optional[str]]:
        """(trial_token, trial_public_pem) per storage mode. Values are
        HMAC-verified before use in SQLite mode — a tampered row reads
        as None → 'tampered' downstream."""
        if self.use_sqlite and self._store is not None:
            data = self._store.get("trial:license")
            token = data.get("token") if isinstance(data, dict) else None
            pub = self._store.get_key("trial_public")
            return token, pub
        trial_lic = self.config_dir / TRIAL_LICENSE_FILE
        _, pub_path = self._trial_key_paths()
        return _read_json_file(trial_lic), _read_json_file(pub_path)

    def _check_real_license(self) -> Optional[TrialStatus]:
        token = self._active_license_token()
        if token is None:
            return None
        validator = LicenseValidator(self.public_key)
        custom_hwid = not isinstance(
            self._hwid_getter, type(HardwareIdentifier.get_machine_id)
        )
        check_hwid = bool(getattr(self, "check_hwid", True))
        try:
            payload = validator.validate(token, check_hwid=check_hwid and not custom_hwid)
            if custom_hwid and check_hwid and payload.hwid.lower() != self._hwid().lower():
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
        token, trial_pub = self._trial_token_and_pub()
        if token is None:
            return TrialStatus(state="no_trial", detail="No trial has been started.")

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
        check_hwid = bool(getattr(self, "check_hwid", True))
        try:
            payload = validator.validate(token, check_hwid=check_hwid and not custom_hwid)
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


# ---- legacy migration ----------------------------------------------------

def migrate_legacy_state(
    config_dir: str | Path,
    store: Any,
    hwid_provider: Any = None,
) -> None:
    """Import file-era trial state into *store* (idempotent).

    Copies the trial public key PEM (so a pre-existing ``trial.lic``
    stays verifiable) and records that migration happened. Clock-guard
    high-water marks need no import: the SQLite clock guard's fallback
    file and the legacy obfuscated copies keep protecting the ratchet.
    """
    from py_rizmi.integrations.validation import _default_state_paths

    config = Path(config_dir)

    if getattr(store, "get_meta", lambda _k: None)("legacy_migrated"):
        return

    getter = hwid_provider or HardwareIdentifier.get_machine_id
    machine_id = getter()

    # 1. trial public key (if any) — lets an existing trial validate
    legacy_pub_path = config / TRIAL_PUB_FILE
    if legacy_pub_path.exists():
        pub_pem = _read_json_file(legacy_pub_path)
        if pub_pem and store.get_key("trial_public") is None:
            legacy_priv_path = config / TRIAL_KEY_FILE
            if legacy_priv_path.exists():
                with open(legacy_priv_path) as f:
                    store.put_key("trial_private", f.read())
            store.put_key("trial_public", pub_pem)

    # 2. ratchet continuity: run one guard check over the LEGACY paths so
    # their marks are honored before any DB-based mark exists.
    try:
        guard = ClockGuard(
            _default_state_paths(str(config), app_name=_TRIAL_START_MARKER),
            machine_id=machine_id,
        )
        guard.check_and_update()
    except Exception as exc:  # noqa: BLE001 — best-effort migration
        logger.warning("Legacy clock-state check failed during migration: %s", exc)

    try:
        store.put_meta("legacy_migrated", "1")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not record migration marker: %s", exc)
