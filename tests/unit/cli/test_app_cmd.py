"""Tests for `rizmi app` — terminal control of an installation's licensing."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from py_rizmi.cli.commands.app_cmd import app

runner = CliRunner()


@pytest.fixture()
def env(tmp_path: Path):
    from py_rizmi.core.keypair import KeyPairManager
    from py_rizmi.models.license_payload import LicensePayload
    from py_rizmi.core.license_issuer import LicenseIssuer
    from py_rizmi.core.hwid import HardwareIdentifier

    priv = tmp_path / "priv.pem"
    pub = tmp_path / "pub.pem"
    KeyPairManager.save_keypair(str(priv), str(pub))
    payload = LicensePayload(
        client="Acme", license_id="L-CLI-1",
        hwid=HardwareIdentifier.get_machine_id(),
    )
    payload.set_auto_iat()
    payload.set_auto_exp(365)
    token = LicenseIssuer.from_file(str(priv)).issue(payload)
    token_file = tmp_path / "license.lic"
    token_file.write_text(token)
    db = tmp_path / "s.db"
    return {"token": token, "file": token_file, "db": db, "app": "CliApp"}


def test_status_fresh_install_is_json(env) -> None:
    res = runner.invoke(app, [
        "status", "--app-name", env["app"], "--db", str(env["db"]), "--json",
    ])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output[res.output.index("{"):])
    assert data["state"] in ("no_trial", "missing", "no_license")


def test_activate_via_file_then_status_licensed(env, tmp_path: Path) -> None:
    from py_rizmi.core.hwid import HardwareIdentifier
    pub = next(p for p in sorted(tmp_path.glob("*.pem")) if "BEGIN PUBLIC KEY" in p.read_text())
    r1 = runner.invoke(app, [
        "activate", "--app-name", env["app"], "--db", str(env["db"]),
        "--public-key", str(pub),
        # the fixture's token is bound to this machine's HWID; pass it so
        # validation matches (simulates activating on THIS machine)
        "--machine-id", HardwareIdentifier.get_machine_id(),
        "--file", str(env["file"]),
    ])
    assert r1.exit_code == 0, r1.output
    res = runner.invoke(app, [
        "status", "--app-name", env["app"], "--db", str(env["db"]), "--json",
    ])
    data = json.loads(res.output[res.output.index("{"):])
    assert data["state"] == "license_row_present"


def test_deactivate_requires_confirm(env, tmp_path: Path) -> None:
    pub = next(p for p in sorted(tmp_path.glob("*.pem")) if "BEGIN PUBLIC KEY" in p.read_text())
    r1 = runner.invoke(app, [
        "activate", "--app-name", env["app"], "--db", str(env["db"]),
        "--public-key", str(pub), "--file", str(env["file"]),
    ])
    assert r1.exit_code == 0
    r2 = runner.invoke(app, ["deactivate", "--app-name", env["app"],
                             "--db", str(env["db"])])
    assert r2.exit_code != 0  # refuses without --confirm
    r3 = runner.invoke(app, ["deactivate", "--app-name", env["app"],
                             "--db", str(env["db"]), "--confirm"])
    assert r3.exit_code == 0


def test_activate_with_stdin_dash(env, tmp_path: Path) -> None:
    pub = next(p for p in sorted(tmp_path.glob("*.pem")) if "BEGIN PUBLIC KEY" in p.read_text())
    # --token - reads the token from stdin (avoids shell history)
    res = runner.invoke(app, [
        "activate", "--app-name", env["app"], "--db", str(env["db"]),
        "--public-key", str(pub),
        "--token", "-",
    ], input=env["token"] + "\n")
    assert res.exit_code == 0, res.output
