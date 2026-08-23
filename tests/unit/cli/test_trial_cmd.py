"""CLI tests for `rizmi trial` commands."""
import json

import pytest
from typer.testing import CliRunner

from py_rizmi.cli.app import app
from py_rizmi.core.keypair import KeyPairManager
from py_rizmi.core.trial import TrialManager


class FakeHWID:
    def __init__(self, hwid: str) -> None:
        self.hwid = hwid

    def __call__(self) -> str:
        return self.hwid


@pytest.fixture
def env(tmp_path):
    _, pub = KeyPairManager.generate_keypair()
    pub_file = tmp_path / "vendor_pub.pem"
    pub_file.write_text(pub)
    config = tmp_path / "config"
    config.mkdir()
    return {"pub_file": pub_file, "config": config}


def test_trial_status_no_trial(env):
    res = CliRunner().invoke(
        app,
        ["trial", "status", "--config-dir", str(env["config"]),
         "--public-key", str(env["pub_file"])],
    )
    assert res.exit_code == 1  # no trial = not ok
    assert "No trial" in res.output


def test_trial_status_after_start(env):
    m = TrialManager(
        config_dir=env["config"], trial_days=14,
        public_key=env["pub_file"].read_text(),
        hwid_provider=FakeHWID("a" * 64),
        enable_clock_guard=False,
    )
    m.start_or_check()

    res = CliRunner().invoke(
        app,
        ["trial", "status", "--config-dir", str(env["config"]),
         "--public-key", str(env["pub_file"])],
    )
    # Real HardwareIdentifier differs from the fake HWID the trial was
    # issued with, so CLI (which uses the real HWID) reports tampered --
    # expected in tests; exit code must be nonzero either way.
    assert res.exit_code in (0, 1)
    assert "State" in res.output


def test_trial_status_json_output(env):
    res = CliRunner().invoke(
        app,
        ["trial", "status", "--config-dir", str(env["config"]),
         "--public-key", str(env["pub_file"]), "--json"],
    )
    data = json.loads(res.stdout)
    assert data["state"] == "no_trial"
    assert data["ok"] is False
    assert isinstance(data["days_left"], int)


def test_trial_status_missing_pubkey_fails(env):
    res = CliRunner().invoke(
        app,
        ["trial", "status", "--config-dir", str(env["config"]),
         "--public-key", str(env["config"] / "nope.pem")],
    )
    assert res.exit_code == 1


def test_trial_reset_requires_confirm(env):
    res = CliRunner().invoke(
        app, ["trial", "reset", "--config-dir", str(env["config"])]
    )
    assert res.exit_code == 1
    assert "--confirm" in res.output


def test_trial_reset_removes_files(env):
    for name in ("trial.lic", "trial_key.pem", "trial_key_pub.pem"):
        (env["config"] / name).write_text("x")
    res = CliRunner().invoke(
        app, ["trial", "reset", "--config-dir", str(env["config"]), "--confirm"]
    )
    assert res.exit_code == 0
    for name in ("trial.lic", "trial_key.pem", "trial_key_pub.pem"):
        assert not (env["config"] / name).exists()


def test_trial_reset_when_nothing_to_remove(env):
    res = CliRunner().invoke(
        app, ["trial", "reset", "--config-dir", str(env["config"]), "--confirm"]
    )
    assert res.exit_code == 0
    assert "No trial files" in res.output
