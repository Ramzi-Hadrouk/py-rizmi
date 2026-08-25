"""ClockGuard storage adapter over the SQLite state store.

Subclasses ``core.clock_guard.ClockGuard`` so the reconciliation and
rollback-refusal logic is inherited untouched; only persistence
(``_read_one``/``_write_all``) is re-routed:

- each clock role lives in a StateStore DB row (role prefix ``clock:``);
- ONE obfuscated fallback file outside the DB keeps working, so
  deleting the whole database cannot reset the high-water mark (and
  vice versa);
- with *shared_clock_path* the mark rows live in a vendor-level shared
  DB so every app from the same vendor advances one collective ratchet.
"""
from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Union

from py_rizmi.core.clock_guard import ClockCheckResult, ClockGuard
from py_rizmi.core.state_store import StateStore

logger = logging.getLogger("license")

_CLOCK_ROLE_PREFIX = "clock:"
_FALLBACK_ROLE = "file-fallback"


class SqliteClockGuard(ClockGuard):
    """ClockGuard whose state lives in a StateStore (+ one fallback file)."""

    def __init__(
        self,
        *,
        db_path: Union[str, Path],
        machine_id: str,
        app_name: str,
        fallback_file: Optional[Union[str, Path]] = None,
        shared_clock_path: Optional[Union[str, Path]] = None,
        tolerance_seconds: int = 300,
        allow_default_namespace: bool = False,
    ) -> None:
        self._store = StateStore(
            db_path,
            machine_id=machine_id,
            app_name=app_name,
            allow_default_namespace=allow_default_namespace,
        )
        self._shared_store: Optional[StateStore] = None
        if shared_clock_path is not None:
            # vendor-level shared ratchet: same machine binding, fixed
            # namespace so all of the vendor's apps converge on one mark
            self._shared_store = StateStore(
                shared_clock_path,
                machine_id=machine_id,
                app_name="shared-clock",
                allow_default_namespace=True,
            )
        self.fallback_file = Path(fallback_file) if fallback_file else None
        self.db_path = self._store.db_path
        super().__init__([_SENTINEL_PATH], machine_id=machine_id,
                         tolerance_seconds=tolerance_seconds)
        # parent stored [sentinel]; replace with our single logical path list
        self.state_paths = []

    # ---- internal helpers -------------------------------------------------

    def _stores(self) -> List[StateStore]:
        stores = [self._store]
        if self._shared_store is not None:
            stores.append(self._shared_store)
        return stores

    def _read_mark(self, store: Optional[StateStore] = None) -> int:
        """Highest verified last_seen_unix across every store's roles."""
        targets = [store] if store is not None else self._stores()
        best = 0
        for target in targets:
            for role in ("primary", "a", "b"):
                data = target.get(_CLOCK_ROLE_PREFIX + role)
                if isinstance(data, dict):
                    value = int(data.get("last_seen_unix", 0))
                    best = max(best, value)
        return best

    def _write_mark(self, last_seen_unix: int) -> List[str]:
        written: List[str] = []
        payload = {"version": 1, "last_seen_unix": int(last_seen_unix)}
        for store in self._stores():
            for role in ("primary", "a", "b"):
                try:
                    store.put(_CLOCK_ROLE_PREFIX + role, payload)
                    written.append(f"{store.db_path}:clock:{role}")
                except Exception as exc:  # noqa: BLE001 — one bad sink ≠ total failure
                    logger.warning(
                        "SqliteClockGuard: could not write %s/%s (%s)",
                        store.db_path, role, exc,
                    )
        if self.fallback_file is not None:
            try:
                encoded = base64.b64encode(
                    json.dumps(payload, separators=(",", ":")).encode("utf-8")
                ).decode("ascii")
                self.fallback_file.parent.mkdir(parents=True, exist_ok=True)
                self.fallback_file.write_text(encoded)
                written.append(str(self.fallback_file))
            except OSError as exc:
                logger.warning(
                    "SqliteClockGuard: could not write fallback file (%s)", exc
                )
        return written

    def _read_fallback(self) -> Tuple[str, Optional[int]]:
        if self.fallback_file is None or not self.fallback_file.exists():
            return "missing", None
        try:
            raw = json.loads(
                base64.b64decode(self.fallback_file.read_text().strip()).decode("utf-8")
            )
            return "valid", int(raw.get("last_seen_unix", 0))
        except Exception:  # noqa: BLE001 — any malformed content is tampering
            return "tampered", None

    # ---- ClockGuard persistence surface ------------------------------------

    def _read_one(self, path: Path) -> Tuple[str, Optional[int]]:  # pragma: no cover
        raise NotImplementedError("SqliteClockGuard routes reads through _read_all")

    def _read_all(self) -> Tuple[int, List[str], List[str], List[str]]:
        valid_values: List[int] = []
        missing: List[str] = []
        tampered: List[str] = []
        db_mark, file_status, file_value = 0, "missing", None
        db_mark = 0
        for store in self._stores():
            for role in ("primary", "a", "b"):
                data, ok = store.get_verified(_CLOCK_ROLE_PREFIX + role)
                if not ok:
                    if data is not None:  # present but failed HMAC → tampered
                        tampered.append(f"{store.db_path}:clock:{role}")
                    else:
                        missing.append(f"{store.db_path}:clock:{role}")
                elif isinstance(data, dict) and int(data.get("last_seen_unix", 0)) > 0:
                    value = int(data.get("last_seen_unix", 0))
                    valid_values.append(value)
                    db_mark = max(db_mark, value)
        file_status, file_value = self._read_fallback()
        if file_status == "valid" and file_value:
            valid_values.append(file_value)
        elif file_status == "tampered":
            tampered.append("fallback-file")
        elif file_status == "missing":
            missing.append("fallback-file")
        last_seen = max(valid_values) if valid_values else 0
        return last_seen, tampered, missing, []

    def _store_is_absent(self, store: StateStore) -> bool:
        return not store.db_path.exists()

    def _write_all(self, last_seen_unix: int) -> List[str]:
        return self._write_mark(last_seen_unix)

    def check_and_update(self, now: Optional[float] = None) -> "ClockCheckResult":
        import time as _time
        from py_rizmi.core.clock_guard import ClockCheckResult

        now = _time.time() if now is None else now
        last_seen, tampered, missing, _recovered = self._read_all()

        if last_seen and now < last_seen - self.tolerance_seconds:
            recovered = self._write_all(last_seen)
            from py_rizmi.core.clock_guard import ClockCheckResult

            return ClockCheckResult(
                ok=False,
                reason="clock_tampering",
                detail=(
                    f"System clock reads {int(now)}, but this installation has "
                    f"already observed {last_seen} (tolerance {self.tolerance_seconds}s)."
                ),
                last_seen_unix=last_seen,
                tampered_paths=tampered,
                missing_paths=missing,
                recovered_paths=recovered,
            )

        new_mark = max(last_seen, int(now))
        recovered = self._write_all(new_mark)
        from py_rizmi.core.clock_guard import ClockCheckResult

        return ClockCheckResult(
            ok=True,
            last_seen_unix=new_mark,
            tampered_paths=tampered,
            missing_paths=missing,
            recovered_paths=recovered,
        )


_SENTINEL_PATH = Path("/dev/null") .__str__()  # never used for IO
