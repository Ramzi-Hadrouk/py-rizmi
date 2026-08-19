"""CLI license swap authorization and secrecy unit tests."""
import json
import pytest
from typer.testing import CliRunner

from py_rizmi.cli.commands.license_cmd import app
from py_rizmi.core.keypair import KeyPairManager
from py_rizmi.core.license_issuer import LicenseIssuer
from py_rizmi.core.swap_auth import create_swap_request
from py_rizmi.models.license_payload import LicensePayload

runner = CliRunner()


@pytest.fixture
def cli_env(tmp_path, sample_payload):
    priv_path = tmp_path / "priv.pem"
    pub_path = tmp_path / "pub.pem"
    KeyPairManager.save_keypair(str(priv_path), str(pub_path))

    issuer = LicenseIssuer.from_file(str(priv_path))
    curr_lic = issuer.issue(sample_payload)

    p2 = LicensePayload.from_dict(sample_payload.to_dict())
    p2.license_id = "cli-replacement-002"
    new_lic = issuer.issue(p2)

    curr_lic_path = tmp_path / "current.lic"
    curr_lic_path.write_text(curr_lic)

    new_lic_path = tmp_path / "new.lic"
    new_lic_path.write_text(new_lic)

    req_payload = create_swap_request(curr_lic, new_lic, request_id="cli-req-123")
    req_file = tmp_path / "request.json"
    req_file.write_text(json.dumps(req_payload.to_dict()))

    return {
        "priv_path": priv_path,
        "pub_path": pub_path,
        "curr_lic_path": curr_lic_path,
        "new_lic_path": new_lic_path,
        "curr_lic": curr_lic,
        "new_lic": new_lic,
        "req_file": req_file,
    }


def test_cli_sign_and_verify_swap(cli_env, tmp_path):
    auth_out = tmp_path / "authorization.rzswap"

    # 1. Test sign-swap CLI command
    res_auth = runner.invoke(
        app,
        [
            "sign-swap",
            "--request",
            str(cli_env["req_file"]),
            "--private-key",
            str(cli_env["priv_path"]),
            "--output",
            str(auth_out),
        ],
    )
    assert res_auth.exit_code == 0
    assert auth_out.exists()

    # 2. Test verify-swap CLI command
    res_verify = runner.invoke(
        app,
        [
            "verify-swap",
            str(auth_out),
            "--public-key",
            str(cli_env["pub_path"]),
            "--current-license",
            str(cli_env["curr_lic_path"]),
            "--new-license",
            str(cli_env["new_lic_path"]),
        ],
    )
    assert res_verify.exit_code == 0
    assert "License swap authorization is valid" in res_verify.stdout


def test_cli_private_key_secrecy(cli_env, tmp_path):
    auth_out = tmp_path / "authorization.rzswap"

    res = runner.invoke(
        app,
        [
            "sign-swap",
            "--request",
            str(cli_env["req_file"]),
            "--private-key",
            str(cli_env["priv_path"]),
            "--output",
            str(auth_out),
        ],
    )
    assert res.exit_code == 0

    for stream in (res.stdout, res.stderr, auth_out.read_text()):
        assert "BEGIN RSA PRIVATE KEY" not in stream
        assert "BEGIN PRIVATE KEY" not in stream
