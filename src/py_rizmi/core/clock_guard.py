"""Local anti-rollback clock integrity checks for offline license validation.

py-Rizmi is designed to run on machines with NO internet connection, so
we cannot lean on NTP or a trusted time server to catch a manipulated
system clock. This module implements two independent, purely-local
signals instead:

  1. A persisted, machine-bound "high water mark" of the latest wall-clock
     time this installation has ever observed. Every check compares the
     current time against it and rejects any large backward jump. This
     is what catches the single most common bypass: close the app, wind
     the OS clock back, reopen the app so an expired/trial license looks
     valid again.

  2. An in-memory monotonic-vs-wall-clock drift check for the current
     process only. `time.monotonic()` is guaranteed by the OS to never
     go backwards and to be unaffected by the wall clock being changed --
     so if monotonic time advances much more than wall time did between
     two checks in the SAME run, the wall clock was frozen or wound back
     *while the app was running*.

On-disk state is base64-obscured (not encrypted -- see module docstring
in the implementation plan for why that distinction matters) and HMAC
protected. Callers are expected to pass multiple *state_paths* in
locations an OS doesn't routinely clear (see integrations.validation for
the reference cross-platform location picker) -- this module only knows
how to read/write/reconcile whatever paths it's given, not where those
paths *should* be; that's deliberately kept as an integrations-layer
concern so core/ stays free of OS/packaging-specific logic.

Threat model: like the RSA-signed license file itself, this raises the
bar against casual-to-moderate tampering (the overwhelming majority of
real-world attempts), not a determined reverse engineer with a debugger
and full disk access. A hardware root of trust (TPM monotonic counter,
secure enclave) is the next step up if that threat model applies to you.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Union

logger = logging.getLogger("license")

# Not a secret from a determined attacker (it ships in the binary) -- its
# only job is to make hand-editing the state file in a text editor
# produce an invalid signature, same trust level as embedding a public key.
_APP_SALT = b"py-rizmi.clock-guard.v1"

_STATE_VERSION = 1

# Single reason string reused by every check in this module, and folded
# into core.license_validator.ERROR_MESSAGES so CLI/GUI/integrations only
# need to handle one new failure category.
REASON = "clock_tampering"

# A copy needs at least this many redundant siblings to make "delete the
# one obvious file" meaningfully harder. Not enforced (a single path is
# still accepted -- e.g. the CLI's diagnostic --clock-state flag wants
# exactly that), just logged, so a real integration doesn't silently
# under-provision redundancy.
_RECOMMENDED_MIN_PATHS = 2


@dataclass
class ClockCheckResult:
    ok: bool
    reason: Optional[str] = None
    detail: str = ""
    last_seen_unix: int = 0
    # Explicit, inspectable outcome of reconciling every configured copy -
    # deliberately separate fields so "someone tampered with a copy" is a
    # distinguishable, loggable event even on a call that still returns
    # ok=True because enough *other* copies were intact.
    tampered_paths: List[str] = field(default_factory=list)
    missing_paths: List[str] = field(default_factory=list)
    recovered_paths: List[str] = field(default_factory=list)


def _derive_key(machine_id: str) -> bytes:
    """Bind the check to this machine so a state file copied from another
    machine can't be used to fake an earlier 'last seen' history here."""
    return hmac.new(_APP_SALT, machine_id.encode("utf-8"), hashlib.sha256).digest()


def _sign(payload: dict, key: bytes) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(key, body, hashlib.sha256).hexdigest()


def _encode(signed: dict) -> str:
    """Base64-obscure the signed JSON payload before it touches disk.

    This is NOT encryption and provides no cryptographic confidentiality
    -- the goal (per the requirement this implements) is only to keep a
    casually curious user from opening the file and immediately
    recognizing readable JSON with keys like "last_seen_unix". The HMAC
    inside is what actually detects tampering; base64 is cosmetic on top.
    """
    raw = json.dumps(signed, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def _decode(text: str) -> dict:
    """Inverse of _encode(). Raises ValueError on any malformed input so
    callers can treat it identically to a failed signature check."""
    try:
        raw = base64.b64decode(text.strip(), validate=True)
        return json.loads(raw)
    except (binascii.Error, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"not a valid clock-guard state blob: {exc}") from exc


class ClockGuard:
    """Detects system-clock rollback for offline license enforcement.

    Pass one or more *state_paths*: redundant copies are written to every
    path given, and a check reads whichever copies exist/verify and
    trusts the highest verified `last_seen_unix` among them. A user has
    to find and wipe *every* copy to reset the ratchet -- meaningfully
    harder than deleting one obvious file. A single path also works
    (a warning is logged, since redundancy is the point) -- e.g. the
    CLI's diagnostic --clock-state flag deliberately uses exactly one.
    """

    def __init__(
        self,
        state_paths: Union[str, Path, List[Union[str, Path]]],
        machine_id: str,
        tolerance_seconds: int = 300,
    ):
        if isinstance(state_paths, (str, Path)):
            state_paths = [state_paths]
        self.state_paths = [Path(p) for p in state_paths]
        self.machine_id = machine_id
        self.tolerance_seconds = tolerance_seconds
        self._key = _derive_key(machine_id)

        if len(self.state_paths) < _RECOMMENDED_MIN_PATHS:
            logger.warning(
                "Clock guard configured with only %d state path(s); redundancy "
                "means a single deleted/corrupted copy can't disable protection "
                "-- consider passing %d or more.",
                len(self.state_paths), _RECOMMENDED_MIN_PATHS,
            )

        # Session state for the monotonic drift check (Layer 2) -- never
        # persisted, intentionally reset every process start.
        self._session_wall0: Optional[float] = None
        self._session_mono0: Optional[float] = None

    # ---- Layer 1: persisted anti-rollback high-water mark --------------

    def _read_one(self, path: Path) -> Tuple[str, Optional[int]]:
        """Classify *path* as ('valid', last_seen_unix), ('missing', None),
        or ('tampered', None). 'missing' covers not-yet-created and any
        OS-level read failure; 'tampered' covers a file that exists but
        fails base64/JSON decoding or HMAC verification."""
        try:
            text = path.read_text()
        except (FileNotFoundError, OSError):
            return "missing", None

        try:
            data = _decode(text)
        except ValueError:
            return "tampered", None

        expected = data.get("hmac")
        payload = {k: v for k, v in data.items() if k != "hmac"}
        if not isinstance(expected, str) or not hmac.compare_digest(
            _sign(payload, self._key), expected
        ):
            return "tampered", None
        try:
            return "valid", int(payload.get("last_seen_unix", 0))
        except (TypeError, ValueError):
            return "tampered", None

    def _write_all(self, last_seen_unix: int) -> List[str]:
        """Write *last_seen_unix* to every configured path. Returns the
        paths that were successfully written (used to populate
        ClockCheckResult.recovered_paths)."""
        payload = {"version": _STATE_VERSION, "last_seen_unix": last_seen_unix}
        signed = {**payload, "hmac": _sign(payload, self._key)}
        text = _encode(signed)
        written: List[str] = []
        for path in self.state_paths:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
                written.append(str(path))
            except OSError as exc:
                # One redundant location being unwritable (e.g. a
                # read-only mount) shouldn't break the whole check.
                logger.warning("Clock guard: could not write state to %s (%s)", path, exc)
        return written

    def check_and_update(self, now: Optional[float] = None) -> ClockCheckResult:
        """Compare *now* (default time.time()) against the persisted high
        water mark, then advance the mark to max(existing, now) and
        rewrite (recover) every configured copy, valid or not."""
        now = time.time() if now is None else now

        valid_values: List[int] = []
        missing_paths: List[str] = []
        tampered_paths: List[str] = []
        for path in self.state_paths:
            status, value = self._read_one(path)
            if status == "valid":
                assert value is not None
                valid_values.append(value)
            elif status == "missing":
                missing_paths.append(str(path))
            else:
                tampered_paths.append(str(path))

        if tampered_paths:
            logger.warning(
                "Clock guard: %d state file(s) failed integrity check (ignored, "
                "not trusted): %s", len(tampered_paths), tampered_paths,
            )

        last_seen_unix = max(valid_values) if valid_values else 0

        if last_seen_unix and now < last_seen_unix - self.tolerance_seconds:
            # Do NOT reward the rollback attempt with a lowered mark --
            # rewrite every copy (including any that were missing or
            # tampered) back to the last known-good value.
            recovered = self._write_all(last_seen_unix)
            return ClockCheckResult(
                ok=False,
                reason=REASON,
                detail=(
                    f"System clock reads {int(now)}, but this installation has "
                    f"already observed {last_seen_unix} (tolerance "
                    f"{self.tolerance_seconds}s)."
                ),
                last_seen_unix=last_seen_unix,
                tampered_paths=tampered_paths,
                missing_paths=missing_paths,
                recovered_paths=recovered,
            )

        new_mark = max(last_seen_unix, int(now))
        recovered = self._write_all(new_mark)
        return ClockCheckResult(
            ok=True,
            last_seen_unix=new_mark,
            tampered_paths=tampered_paths,
            missing_paths=missing_paths,
            recovered_paths=recovered,
        )

    # ---- Layer 2: intra-session monotonic drift check -------------------

    def start_session(self, now: Optional[float] = None) -> None:
        """Call once at process startup, before the first drift check."""
        self._session_wall0 = time.time() if now is None else now
        self._session_mono0 = time.monotonic()

    def check_session_drift(self, now: Optional[float] = None) -> ClockCheckResult:
        """Compare elapsed wall-clock time to elapsed monotonic time since
        start_session(). Only flags the wall clock lagging BEHIND
        monotonic time (rolled back or frozen) -- a wall clock jumping
        far AHEAD of monotonic (laptop sleep/resume, an NTP forward
        correction) is not tampering and is deliberately not flagged.
        """
        if self._session_wall0 is None or self._session_mono0 is None:
            self.start_session(now)
            return ClockCheckResult(ok=True)

        now = time.time() if now is None else now
        wall_delta = now - self._session_wall0
        mono_delta = time.monotonic() - self._session_mono0

        if mono_delta - wall_delta > self.tolerance_seconds:
            return ClockCheckResult(
                ok=False,
                reason=REASON,
                detail=(
                    f"{mono_delta:.0f}s of real time passed but the system clock "
                    f"only advanced {wall_delta:.0f}s since this session started."
                ),
            )
        return ClockCheckResult(ok=True)
