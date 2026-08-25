"""Frozen-build smoke entry point.

Compiled with Nuitka/PyInstaller by tests/e2e/test_frozen_smoke.py.
Exercises StateStore + TrialManager(use_sqlite=True) inside a real
binary. Exit 0 = flow OK; exit 3 = tamper detection failed; exit 4 =
unexpected error. With SMOKE_TAMPER=1 the DB is corrupted first and a
nonzero exit is EXPECTED (detection works).
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from py_rizmi._internal.env import is_frozen, packager
from py_rizmi.core.keypin import key_fingerprint, pin_fingerprint
from py_rizmi.core.state_store import StateStoreError
from py_rizmi.core.trial import TrialManager


def _make_keypair(tmp: Path) -> str:
    from py_rizmi.core.crypto import generate_rsa_keypair

    priv_pem, pub_pem = generate_rsa_keypair(2048)
    pin_fingerprint(pub_pem, key_fingerprint(pub_pem))  # self-check sanity
    (tmp / "trial_priv.pem").write_text(priv_pem)
    return pub_pem


def main() -> int:
    print(f"frozen={is_frozen()} packager={packager()}")
    tmp = Path(tempfile.mkdtemp(prefix="rizmi-smoke-"))
    pub_pem = _make_keypair(tmp)

    db_path = tmp / "state.db"
    fallback = tmp / "fb.dat"
    config_dir = tmp / "cfg"

    tm = TrialManager(
        config_dir,
        trial_days=14,
        public_key=pub_pem,
        use_sqlite=True,
        db_path=db_path,
        clock_fallback_file=fallback,
        app_name="SmokeApp",
        allow_default_namespace=False,
    )
    status = tm.start_or_check()
    if status.state != "trial_active":
        print(f"FAIL: expected trial_active, got {status.state}: {status.detail}")
        return 4
    print(f"trial active, days_left={status.days_left}")

    # second manager instance reads the same DB fine (interop)
    tm2 = TrialManager(
        config_dir,
        trial_days=14,
        public_key=pub_pem,
        use_sqlite=True,
        db_path=db_path,
        clock_fallback_file=fallback,
        app_name="SmokeApp",
    )
    status2 = tm2.check()
    if status2.state != "trial_active":
        print(f"FAIL: interop check got {status2.state}")
        return 4

    if os.environ.get("SMOKE_TAMPER") == "1":
        import sqlite3

        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE keys SET pem='forged-pem' WHERE role='trial_public'")
            conn.commit()
        status3 = tm2.check()
        if status3.state != "tampered":
            print(f"FAIL: tamper not detected, got {status3.state}")
            return 3
        print("tamper detected OK")

    if not is_frozen():
        # running under plain python is fine too — just report it
        print("(not frozen; informational)")

    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except StateStoreError as exc:
        print(f"FAIL: {exc}")
        sys.exit(4)
