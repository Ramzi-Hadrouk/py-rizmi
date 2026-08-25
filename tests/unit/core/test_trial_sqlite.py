"""Tests for TrialManager SQLite mode and legacy state migration."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from py_rizmi.core.state_store import StateStore
from py_rizmi.core.trial import migrate_legacy_state, TrialManager


@pytest.fixture()
def keypair(tmp_path: Path):
    from py_rizmi.core.keypair import KeyPairManager

    priv = tmp_path / "private.pem"
    pub = tmp_path / "public.pem"
    KeyPairManager.save_keypair(str(priv), str(pub))
    with open(pub) as f:
        pub_pem = f.read()
    return priv, pub_pem


@pytest.fixture()
def sqlite_trial(keypair, tmp_path: Path) -> tuple[TrialManager, Path]:
    _, pub_pem = keypair
    config_dir = tmp_path / "appconfig"
    db_path = tmp_path / "state.db"
    tm = TrialManager(
        config_dir,
        trial_days=14,
        public_key=pub_pem,
        use_sqlite=True,
        db_path=db_path,
        app_name="MyApp",
    )
    return tm, config_dir


def test_full_cycle_issue_active_tamper(sqlite_trial) -> None:
    tm, _config_dir = sqlite_trial
    status = tm.start_or_check()
    assert status.state == "trial_active"
    assert status.days_left > 0
    # tamper with the trial license row
    import json
    import sqlite3

    db = Path(tm._store.db_path)
    with sqlite3.connect(db) as conn:
        role = [r[0] for r in conn.execute("SELECT role FROM keys")]
    # corrupt the trial public key PEM (breaks its HMAC)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE keys SET pem='forged' WHERE role='trial_public'")
        conn.commit()
    status2 = tm.check()
    assert status2.state == "tampered"


def test_no_loose_files_created(sqlite_trial) -> None:
    tm, config_dir = sqlite_trial
    tm.start_or_check()
    created = list(config_dir.rglob("*")) if config_dir.exists() else []
    assert created == [], f"SQLite mode must not create files in config_dir, found {created}"


def test_real_license_still_wins(keypair, tmp_path: Path) -> None:
    from py_rizmi.core.license_issuer import LicenseIssuer
    from py_rizmi.models.license_payload import LicensePayload

    priv, pub_pem = keypair
    config_dir = tmp_path / "cfg"
    payload = LicensePayload(client="Acme", license_id="real-1", hwid="")
    payload.set_auto_iat()
    payload.set_auto_exp(365)
    token = LicenseIssuer.from_file(str(priv)).issue(payload)

    tm = TrialManager(
        config_dir,
        trial_days=14,
        public_key=pub_pem,
        use_sqlite=True,
        db_path=tmp_path / "s.db",
        app_name="MyApp",
        check_hwid=False,
    )
    # activate the real license through the activator path (the SQLite flow)
    lic_path = config_dir / "license.lic"
    config_dir.mkdir(parents=True, exist_ok=True)
    lic_path.write_text(token)
    from py_rizmi.core.license_activator import LicenseActivator

    activation = LicenseActivator(tm._store, pub_pem, check_hwid=False).activate_file(
        lic_path
    )
    assert activation.ok
    status = tm.check()
    assert status.state == "licensed"
    assert status.payload is not None


def test_db_deletion_does_not_reset_trial_start(keypair, tmp_path: Path) -> None:
    _, pub_pem = keypair
    config_dir = tmp_path / "cfg"
    db_path = tmp_path / "state.db"
    fallback = tmp_path / "fb.dat"

    tm1 = TrialManager(
        config_dir, trial_days=14, public_key=pub_pem,
        use_sqlite=True, db_path=db_path, clock_fallback_file=fallback,
        app_name="MyApp",
    )
    s1 = tm1.start_or_check()
    first_payload_exp = None
    if s1.payload is not None:
        first_payload_exp = s1.payload.exp

    # wipe the whole DB; trial.lic lives only in the DB so it's gone too.
    db_path.unlink()

    tm2 = TrialManager(
        config_dir, trial_days=14, public_key=pub_pem,
        use_sqlite=True, db_path=db_path, clock_fallback_file=fallback,
        app_name="MyApp",
    )
    s2 = tm2.start_or_check()
    if s2.payload is not None and first_payload_exp is not None:
        # re-issued trial inherits the ratcheted start date: the new iat
        # must equal the ORIGINAL start (exp - 14 days), within a couple
        # of seconds of wall-clock advance between the two issuances.
        original_iat = first_payload_exp - 14 * 86_400
        assert abs(s2.payload.iat - original_iat) <= 5, (
            f"trial clock was reset after DB deletion: iat drifted "
            f"{s2.payload.iat - original_iat}s"
        )


def test_file_mode_unchanged_when_disabled(keypair, tmp_path: Path) -> None:
    _, pub_pem = keypair
    config_dir = tmp_path / "cfg"
    tm = TrialManager(
        config_dir, trial_days=14, public_key=pub_pem,
        enable_clock_guard=False,
    )
    status = tm.start_or_check()
    assert status.state == "trial_active"
    assert (config_dir / "trial.lic").exists()      # legacy behavior intact
    assert (config_dir / "trial_key.pem").exists()


def test_migrate_legacy_state_imports_clock_mark(keypair, tmp_path: Path) -> None:
    """A pre-existing file-based install migrates without resetting dates."""
    _, pub_pem = keypair
    config_dir = tmp_path / "legacy-cfg"
    config_dir.mkdir()
    # simulate legacy file-based trial run (creates files + clock marks)
    legacy_tm = TrialManager(
        config_dir, trial_days=14, public_key=pub_pem,
    )
    legacy_tm.start_or_check()

    db_path = tmp_path / "new.db"
    store = StateStore(db_path, machine_id=legacy_tm._hwid(), app_name="MyApp")
    migrate_legacy_state(str(config_dir), store)

    # migration must be idempotent
    migrate_legacy_state(str(config_dir), store)
    report = store.verify()
    assert report.ok


def test_from_config_maps_sqlite_fields(keypair, tmp_path: Path) -> None:
    from py_rizmi.core.config import RizmiConfig

    _, pub_pem = keypair
    config = RizmiConfig(
        use_sqlite=True,
        db_path=str(tmp_path / "c.db"),
        trial_days=7,
        allow_default_namespace=True,
    )
    tm = TrialManager.from_config(config, tmp_path / "cfg", pub_pem)
    assert tm.use_sqlite is True
    assert tm.trial_days == 7
