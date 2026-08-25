"""Tests for `rizmi keys fingerprint` and trial CLI SQLite awareness."""
from __future__ import annotations

from typer.testing import CliRunner

from py_rizmi.cli.commands.keys import app as keys_app

runner = CliRunner()


def test_fingerprint_command_prints_sha256(tmp_path):
    from py_rizmi.core.keypair import KeyPairManager

    pub = tmp_path / "pub.pem"
    priv = tmp_path / "priv.pem"
    KeyPairManager.save_keypair(str(priv), str(pub))
    res = runner.invoke(keys_app, ["fingerprint", "--public", str(pub)])
    assert res.exit_code == 0, res.output
    # 64-hex digest appears in the output
    import re

    match = re.search(r"\b[0-9a-f]{64}\b", res.output)
    assert match, res.output


def test_fingerprint_missing_file_errors():
    res = runner.invoke(keys_app, ["fingerprint", "--public", "/nope/missing.pem"])
    assert res.exit_code == 1
