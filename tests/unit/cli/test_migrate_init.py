"""Tests for `rizmi migrate-to-sqlite` and `rizmi init`."""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture()
def legacy_install(tmp_path: Path):
    """A file-era trial install."""
    from py_rizmi.core.keypair import KeyPairManager
    from py_rizmi.core.trial import TrialManager

    pub = tmp_path / "pub.pem"
    priv = tmp_path / "priv.pem"
    KeyPairManager.save_keypair(str(priv), str(pub))
    pub_pem = pub.read_text()
    config_dir = tmp_path / "cfg"
    tm = TrialManager(config_dir, trial_days=14, public_key=pub_pem)
    status = tm.start_or_check()
    assert status.state == "trial_active"
    return {"config_dir": config_dir, "pub": pub, "db": tmp_path / "new.db"}


def test_migrate_to_sqlite_imports_and_is_idempotent(legacy_install) -> None:
    from py_rizmi.cli.commands.migrate_cmd import app as migrate_app
    from py_rizmi.core.hwid import HardwareIdentifier
    from py_rizmi.core.state_store import StateStore

    env = legacy_install
    res = runner.invoke(migrate_app, [
        "--config-dir", str(env["config_dir"]),
        "--app-name", "MyApp",
        "--db", str(env["db"]),
    ])
    assert res.exit_code == 0, res.output
    store = StateStore(str(env["db"]), machine_id=HardwareIdentifier.get_machine_id(),
                       app_name="MyApp")
    assert store.verify().ok
    # second run reports already-migrated and still exits 0
    res2 = runner.invoke(migrate_app, [
        "--config-dir", str(env["config_dir"]),
        "--app-name", "MyApp",
        "--db", str(env["db"]),
    ])
    assert res2.exit_code == 0
    assert "already" in res2.output.lower()


def test_init_scaffolder(tmp_path: Path) -> None:
    from py_rizmi.cli.commands.init_cmd import app as init_app
    from py_rizmi.core.keypin import key_fingerprint

    out = tmp_path / "licensing"
    res = runner.invoke(init_app, ["MyApp", "--out", str(out)])
    assert res.exit_code == 0, res.output
    assert (out / "private_key.pem").exists()
    assert (out / "public_key.pem").exists()
    expected_fp = key_fingerprint((out / "public_key.pem").read_text())
    assert expected_fp in res.output          # fingerprint printed for pasting
    assert "LicenseGate" in res.output        # ready-to-paste snippet included


def test_init_refuses_existing_output(tmp_path: Path) -> None:
    from py_rizmi.cli.commands.init_cmd import app as init_app

    out = tmp_path / "licensing"
    out.mkdir()
    (out / "private_key.pem").write_text("existing")
    res = runner.invoke(init_app, ["MyApp", "--out", str(out)])
    assert res.exit_code == 1
