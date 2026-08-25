"""Tests for `rizmi doctor` — installation health checklist."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from py_rizmi.cli.commands.doctor import app

runner = CliRunner()


@pytest.fixture()
def licensed_env(tmp_path: Path):
    """A working install: keypair, activated license, trial started."""
    from py_rizmi.core.hwid import HardwareIdentifier
    from py_rizmi.core.license_issuer import LicenseIssuer
    from py_rizmi.core.keypair import KeyPairManager
    from py_rizmi.core.license_activator import LicenseActivator
    from py_rizmi.core.state_store import StateStore
    from py_rizmi.models.license_payload import LicensePayload

    priv = tmp_path / "priv.pem"
    pub = tmp_path / "pub.pem"
    KeyPairManager.save_keypair(str(priv), str(pub))
    pub_pem = pub.read_text()
    payload = LicensePayload(
        client="Acme", license_id="L-DOC-1",
        hwid=HardwareIdentifier.get_machine_id(),
    )
    payload.set_auto_iat()
    payload.set_auto_exp(365)
    token = LicenseIssuer.from_file(str(priv)).issue(payload)
    db = tmp_path / "s.db"
    store = StateStore(db, machine_id=HardwareIdentifier.get_machine_id(),
                       app_name="DocApp")
    LicenseActivator(store, pub_pem).activate_token(token)
    return {"db": db, "pub": pub, "pub_pem": pub_pem}


def test_doctor_all_green_on_healthy_install(licensed_env) -> None:
    res = runner.invoke(app, [
        "--app-name", "DocApp", "--db", str(licensed_env["db"]),
        "--public-key", str(licensed_env["pub"]),
    ])
    assert res.exit_code == 0, res.output
    assert "✓" in res.output or "PASS" in res.output.upper() or "ok" in res.output.lower()


def test_doctor_json_output_parseable(licensed_env) -> None:
    res = runner.invoke(app, [
        "--app-name", "DocApp", "--db", str(licensed_env["db"]),
        "--public-key", str(licensed_env["pub"]), "--json",
    ])
    assert res.exit_code == 0
    data = json.loads(res.output[res.output.index("["):res.output.rindex("]") + 1])
    assert isinstance(data, list) and len(data) >= 4
    names = [item["check"] for item in data]
    assert any("machine" in n.lower() for n in names)


def test_doctor_detects_tampered_db_strict(tmp_path, licensed_env) -> None:
    import sqlite3

    with sqlite3.connect(licensed_env["db"]) as conn:
        conn.execute("UPDATE licenses SET token='forged' WHERE slot='active'")
        conn.commit()
    res = runner.invoke(app, [
        "--app-name", "DocApp", "--db", str(licensed_env["db"]),
        "--public-key", str(licensed_env["pub"]), "--strict",
    ])
    assert res.exit_code != 0


def test_doctor_fingerprint_mismatch_detected(licensed_env) -> None:
    res = runner.invoke(app, [
        "--app-name", "DocApp", "--db", str(licensed_env["db"]),
        "--public-key", str(licensed_env["pub"]),
        "--fingerprint", "0" * 64,
    ])
    assert res.exit_code != 0
