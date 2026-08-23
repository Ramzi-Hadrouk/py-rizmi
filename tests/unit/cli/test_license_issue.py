"""CLI tests for `rizmi license issue` argument validation (Phase 2)."""
import pytest
from typer.testing import CliRunner

from py_rizmi.cli.commands.license_cmd import app
from py_rizmi.core.keypair import KeyPairManager

runner = CliRunner()


@pytest.fixture
def keypair(tmp_path):
    priv = tmp_path / "priv.pem"
    pub = tmp_path / "pub.pem"
    KeyPairManager.save_keypair(str(priv), str(pub))
    return priv, pub


def _issue_args(priv, **overrides):
    args = [
        "issue",
        "--private-key", str(priv),
        "--client", "Acme",
        "--license-id", "L-1",
        "--hwid", "a" * 64,
        "--output", str(overrides.pop("output")),
    ]
    for flag, value in overrides.items():
        args.extend([flag, str(value)])
    return args


class TestIssueArgumentValidation:
    def test_happy_path_succeeds(self, keypair, tmp_path):
        priv, _ = keypair
        out = tmp_path / "ok.lic"
        res = runner.invoke(app, _issue_args(priv, output=out))
        assert res.exit_code == 0, res.output
        assert out.exists()

    @pytest.mark.parametrize("flag,bad", [("--exp-days", 0), ("--exp-days", -5)])
    def test_non_positive_exp_days_rejected(self, keypair, tmp_path, flag, bad):
        priv, _ = keypair
        res = runner.invoke(app, _issue_args(priv, output=tmp_path / "x.lic", **{flag: bad}))
        assert res.exit_code == 1
        assert "exp-days" in res.output

    def test_negative_grace_days_rejected(self, keypair, tmp_path):
        priv, _ = keypair
        res = runner.invoke(
            app, _issue_args(priv, output=tmp_path / "x.lic", **{"--grace-days": -1})
        )
        assert res.exit_code == 1
        assert "grace-days" in res.output

    @pytest.mark.parametrize("bad", [0, -3])
    def test_invalid_max_clients_rejected(self, keypair, tmp_path, bad):
        priv, _ = keypair
        res = runner.invoke(
            app, _issue_args(priv, output=tmp_path / "x.lic", **{"--max-clients": bad})
        )
        assert res.exit_code == 1
        assert "max-clients" in res.output

    def test_online_mode_requires_server_url(self, keypair, tmp_path):
        priv, _ = keypair
        res = runner.invoke(
            app, _issue_args(priv, output=tmp_path / "x.lic", **{"--mode": "online"})
        )
        assert res.exit_code == 1
        assert "server-url" in res.output

    def test_online_mode_with_server_url_accepted(self, keypair, tmp_path):
        priv, _ = keypair
        res = runner.invoke(
            app,
            _issue_args(
                priv,
                output=tmp_path / "x.lic",
                **{"--mode": "online", "--server-url": "https://lic.example.com"},
            ),
        )
        assert res.exit_code == 0, res.output
