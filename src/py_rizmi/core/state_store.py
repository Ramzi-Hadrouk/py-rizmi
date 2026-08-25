"""SQLite-backed tamper-evident state store.

Storage is UNTRUSTED: every value is verified against a machine- and
app-bound HMAC before use (same trust model as ``core.clock_guard`` --
the key ships in the binary; its job is making hand-editing or
cross-app transplanting produce invalid signatures, not to resist a
determined reverse engineer).

Namespacing (multi-app machines)
--------------------------------
The MAC key is derived from BOTH the machine id AND *app_name*, and the
constructor refuses the toolkit-default name ``"py-rizmi"`` unless
``allow_default_namespace=True`` (tests/diagnostics only). Two apps that
share a machine therefore cannot read, overwrite, or transplant each
other's state: each app must pass its own product name.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("license")

_APP_SALT = b"py-rizmi.sqlite.v2"
_SCHEMA_VERSION = "2"
DEFAULT_TOOLKIT_NAME = "py-rizmi"


class StateStoreError(RuntimeError):
    """Raised for structural store problems (schema, bad configuration)."""


@dataclass
class StoredLicense:
    license_id: str
    token: str
    activated_at: int


@dataclass
class StoreIntegrityReport:
    ok: bool
    tampered_roles: List[str] = field(default_factory=list)


def _derive_store_key(machine_id: str, app_name: str) -> bytes:
    """HKDF-style derivation binding the MAC to machine AND app."""
    ikm = hashlib.sha256(machine_id.encode("utf-8")).digest()
    prk = hmac.new(_APP_SALT, ikm, hashlib.sha256).digest()
    return hmac.new(prk, f"store-mac:{app_name}".encode("utf-8"), hashlib.sha256).digest()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS store_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS keys (
    role       TEXT PRIMARY KEY,
    pem        TEXT NOT NULL,
    hmac       TEXT NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS state (
    role       TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    hmac       TEXT NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS licenses (
    license_id   TEXT PRIMARY KEY,
    slot         TEXT NOT NULL UNIQUE DEFAULT 'active',
    token        TEXT NOT NULL,
    hmac         TEXT NOT NULL,
    activated_at INTEGER NOT NULL
);
"""


class StateStore:
    """Keyed, tamper-evident single-file SQLite store.

    Parameters
    ----------
    db_path:
        Location of the database file. Use ``default_path()`` (or your
        own platformdirs-based path); never derive it from ``__file__``
        -- frozen builds extract to temp directories.
    machine_id:
        This machine's fingerprint (e.g. ``HardwareIdentifier.get_machine_id()``).
    app_name:
        Your product's name. MUST differ from the toolkit default;
        see the module docstring for why.
    allow_default_namespace:
        Escape hatch for tests/diagnostics only.
    """

    def __init__(
        self,
        db_path: Union[str, Path],
        *,
        machine_id: str,
        app_name: str,
        allow_default_namespace: bool = False,
    ) -> None:
        if not machine_id or not isinstance(machine_id, str):
            raise ValueError("machine_id must be a non-empty string")
        if not app_name or not isinstance(app_name, str):
            raise ValueError("app_name must be a non-empty string")
        if app_name == DEFAULT_TOOLKIT_NAME and not allow_default_namespace:
            raise StateStoreError(
                "app_name must be your own product name, not the toolkit default "
                "'py-rizmi' -- per-app namespacing prevents cross-app state "
                "conflicts on shared machines. Pass allow_default_namespace=True "
                "only in tests/diagnostics."
            )
        self.db_path = Path(db_path)
        self.app_name = app_name
        self._key = _derive_store_key(machine_id, app_name)
        self._ensure_schema()

    # ── plumbing ──────────────────────────────────────────────────────

    @staticmethod
    def default_path(app_name: str) -> Path:
        """Writable, persistent, per-app DB location (never __file__-derived)."""
        from py_rizmi.integrations.validation import _platform_dirs

        dir_a, _ = _platform_dirs(app_name)
        return Path(dir_a) / "state.db"

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA synchronous=FULL")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            row = conn.execute(
                "SELECT value FROM store_meta WHERE key='schema_version'"
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO store_meta(key, value) VALUES ('schema_version', ?)",
                    [_SCHEMA_VERSION],
                )
                conn.execute(
                    "INSERT OR REPLACE INTO store_meta(key, value) VALUES ('app_name', ?)",
                    [self.app_name],
                )
                conn.execute(
                    "INSERT INTO store_meta(key, value) VALUES ('created_at', ?)",
                    [str(int(time.time()))],
                )
            elif row[0] != _SCHEMA_VERSION:
                raise StateStoreError(
                    f"state DB schema version {row[0]!r} is not supported "
                    f"(expected {_SCHEMA_VERSION!r})"
                )

    def _mac(self, table: str, role: str, blob: bytes) -> str:
        return hmac.new(
            self._key, f"{table}:{role}:".encode("utf-8") + blob, hashlib.sha256
        ).hexdigest()

    @staticmethod
    def _canonical(payload: Dict[str, Any]) -> bytes:
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    # ── generic state roles ───────────────────────────────────────────

    def put(self, role: str, payload: Dict[str, Any]) -> None:
        blob = self._canonical(payload)
        mac = self._mac("state", role, blob)
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO state(role, payload, hmac, updated_at) "
                "VALUES (?, ?, ?, ?)",
                [role, blob.decode("ascii"), mac, int(time.time())],
            )

    def get(self, role: str) -> Optional[Dict[str, Any]]:
        """Return the payload only when its HMAC verifies; None otherwise."""
        data, ok = self.get_verified(role)
        return data if ok else None

    def get_verified(self, role: str) -> Tuple[Optional[Dict[str, Any]], bool]:
        """Return (payload, verified). verified=False covers both a
        missing role (payload None) and a present-but-tampered role."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT payload, hmac FROM state WHERE role = ?", [role]
                ).fetchone()
        except sqlite3.DatabaseError:
            # unreadable/foreign file: treat as missing, never crash callers
            return None, False
        if row is None:
            return None, False
        payload_text, expected = str(row[0]), str(row[1])
        if not hmac.compare_digest(
            self._mac("state", role, payload_text.encode("utf-8")), expected
        ):
            logger.warning("State store: role %r failed integrity check", role)
            try:
                forged: Dict[str, Any] = json.loads(payload_text)
            except json.JSONDecodeError:
                return None, False
            return forged, False
        result: Dict[str, Any] = json.loads(payload_text)
        return result, True

    def delete(self, role: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM state WHERE role = ?", [role])

    # ── meta ──────────────────────────────────────────────────────────

    def put_meta(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO store_meta(key, value) VALUES (?, ?)",
                [key, value],
            )

    def get_meta(self, key: str) -> Optional[str]:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT value FROM store_meta WHERE key = ?", [key]
                ).fetchone()
        except sqlite3.DatabaseError:
            return None
        return str(row[0]) if row else None

    # ── key material ──────────────────────────────────────────────────

    def put_key(self, role: str, pem: str) -> None:
        blob = pem.encode("utf-8")
        mac = self._mac("keys", role, blob)
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO keys(role, pem, hmac, updated_at) "
                "VALUES (?, ?, ?, ?)",
                [role, pem, mac, int(time.time())],
            )

    def get_key(self, role: str) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT pem, hmac FROM keys WHERE role = ?", [role]
            ).fetchone()
        if row is None:
            return None
        pem, expected = str(row[0]), str(row[1])
        if not hmac.compare_digest(
            self._mac("keys", role, pem.encode("utf-8")), expected
        ):
            logger.warning("State store: key %r failed integrity check", role)
            return None
        return pem

    # ── licenses ──────────────────────────────────────────────────────

    def put_license(self, token: str, *, license_id: str) -> StoredLicense:
        blob = token.encode("utf-8")
        mac = self._mac("licenses", license_id, blob)
        now = int(time.time())
        with self._connect() as conn:
            # single active slot: demote any previous holder atomically
            conn.execute("UPDATE licenses SET slot='archived' WHERE slot='active'")
            conn.execute(
                "INSERT OR REPLACE INTO licenses"
                "(license_id, slot, token, hmac, activated_at) "
                "VALUES (?, 'active', ?, ?, ?)",
                [license_id, token, mac, now],
            )
        return StoredLicense(license_id=license_id, token=token, activated_at=now)

    def get_license(self, license_id: str) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT token, hmac FROM licenses WHERE license_id = ?", [license_id]
            ).fetchone()
        if row is None:
            return None
        token, expected = str(row[0]), str(row[1])
        if not hmac.compare_digest(
            self._mac("licenses", license_id, token.encode("utf-8")), expected
        ):
            logger.warning(
                "State store: license %r failed integrity check", license_id
            )
            return None
        return token

    def active_license(self) -> Optional[StoredLicense]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT license_id, token, activated_at FROM licenses "
                "WHERE slot='active'"
            ).fetchone()
        if row is None:
            return None
        license_id, token, activated_at = row
        if not hmac.compare_digest(
            self._mac("licenses", license_id, token.encode("utf-8")),
            self._active_hmac(license_id),
        ):
            logger.warning(
                "State store: active license %r failed integrity check", license_id
            )
            return None
        return StoredLicense(
            license_id=license_id, token=token, activated_at=int(activated_at)
        )

    def _active_hmac(self, license_id: str) -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT hmac FROM licenses WHERE slot='active' AND license_id=?",
                [license_id],
            ).fetchone()
        return row[0] if row else ""

    # ── integrity report ──────────────────────────────────────────────

    def verify(self) -> StoreIntegrityReport:
        tampered: List[str] = []
        with self._connect() as conn:
            for role, payload_text, expected in conn.execute(
                "SELECT role, payload, hmac FROM state"
            ):
                if not hmac.compare_digest(
                    self._mac("state", role, payload_text.encode("utf-8")), expected
                ):
                    tampered.append(f"state:{role}")
            for role, pem, expected in conn.execute(
                "SELECT role, pem, hmac FROM keys"
            ):
                if not hmac.compare_digest(
                    self._mac("keys", role, pem.encode("utf-8")), expected
                ):
                    tampered.append(f"keys:{role}")
            for license_id, token, expected in conn.execute(
                "SELECT license_id, token, hmac FROM licenses"
            ):
                if not hmac.compare_digest(
                    self._mac("licenses", license_id, token.encode("utf-8")), expected
                ):
                    tampered.append(f"licenses:{license_id}")
        return StoreIntegrityReport(ok=not tampered, tampered_roles=tampered)
