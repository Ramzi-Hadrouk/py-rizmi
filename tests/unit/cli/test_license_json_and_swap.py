"""CLI Phase 4 tests: --json output, issue --from-json, swap request generation."""
import json

import pytest
from typer.testing import CliRunner

from py_rizmi.cli.commands.license_cmd import app
from py_rizmi.cli.commands.machine_id import app as machine_id_app
from py_rizmi.core.keypair import KeyPairManager
from py_rizmi.core.license_issuer import LicenseIssuer
from py_rizmi.models.license_payload import LicensePayload

runner = CliRunner()


@pytest.fixture
def env(tmp_path, sample_payload):
    priv = tmp_path / "priv.pem"
    pub = tmp_path / "pub.pem"
    KeyPairManager.save_keypair(str(priv), str(pub))
    issuer = LicenseIssuer.from_file(str(priv))
    lic = tmp_path / "test.lic"
    lic.write_text(issuer.issue(sample_payload))
    return {"priv": priv, "pub": pub, "lic": lic}


class TestJsonOutput:
    def test_validate_json_is_parseable(self, env):
        res = runner.invoke(
            app,
            ["validate", str(env["lic"]), "--public-key", str(env["pub"]), "--json"],
        )
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert data["valid"] is True
        assert "client" in data and "exp" in data

    def test_inspect_json_is_parseable(self, env):
        res = runner.invoke(
            app,
            ["inspect", str(env["lic"]), "--public-key", str(env["pub"]), "--json"],
        )
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert "license_id" in data
        # inspect output must NOT contain the validate-only marker
        assert "valid" not in data

    def test_machine_id_json_is_parseable(self):
        res = runner.invoke(machine_id_app, ["--json"])
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert len(data["hwid"]) == 64
        assert data["algorithm"] == "sha256"


class TestIssueFromJson:
    def test_issue_with_spec_file(self, env, tmp_path):
        spec = tmp_path / "spec.json"
        spec.write_text(json.dumps({
            "client": "SpecClient",
            "license_id": "SPEC-001",
            "hwid": "b" * 64,
            "features": ["pro", "beta"],
            "max_clients": 25,
            "grace_days": 7,
        }))
        out = tmp_path / "spec.lic"
        res = runner.invoke(
            app,
            [
                "issue", "--private-key", str(env["priv"]),
                "--from-json", str(spec), "--output", str(out),
            ],
        )
        assert res.exit_code == 0, res.output

        # Round-trip through inspect to confirm the spec was applied.
        insp = runner.invoke(
            app, ["inspect", str(out), "--public-key", str(env["pub"]), "--json"]
        )
        data = json.loads(insp.stdout)
        assert data["client"] == "SpecClient"
        assert data["license_id"] == "SPEC-001"
        assert data["features"] == ["pro", "beta"]
        assert data["max_clients"] == 25
        assert data["grace_days"] == 7

    def test_explicit_flags_override_spec(self, env, tmp_path):
        spec = tmp_path / "spec.json"
        spec.write_text(json.dumps({"client": "FromFile", "license_id": "X", "hwid": "c" * 64}))
        out = tmp_path / "over.lic"
        res = runner.invoke(
            app,
            [
                "issue", "--private-key", str(env["priv"]),
                "--from-json", str(spec),
                "--client", "FromFlag",
                "--output", str(out),
            ],
        )
        assert res.exit_code == 0, res.output
        insp = runner.invoke(
            app, ["inspect", str(out), "--public-key", str(env["pub"]), "--json"]
        )
        assert json.loads(insp.stdout)["client"] == "FromFlag"

    def test_invalid_spec_file_rejected(self, env, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not json")
        res = runner.invoke(
            app,
            ["issue", "--private-key", str(env["priv"]), "--from-json", str(bad),
             "--output", str(tmp_path / "x.lic")],
        )
        assert res.exit_code == 1

    def test_non_object_spec_rejected(self, env, tmp_path):
        bad = tmp_path / "arr.json"
        bad.write_text("[1,2,3]")
        res = runner.invoke(
            app,
            ["issue", "--private-key", str(env["priv"]), "--from-json", str(bad),
             "--output", str(tmp_path / "x.lic")],
        )
        assert res.exit_code == 1


class TestCreateSwapRequest:
    def test_create_then_sign_then_verify_roundtrip(self, env, tmp_path, sample_payload):
        pub = env["pub"]
        issuer = LicenseIssuer.from_file(str(env["priv"]))
        new_lic = tmp_path / "new.lic"
        p2 = LicensePayload.from_dict(sample_payload.to_dict())
        p2.license_id = "swap-target-002"
        new_lic.write_text(issuer.issue(p2))

        req = tmp_path / "req.json"
        res = runner.invoke(
            app,
            [
                "create-swap-request",
                "--current-license", str(env["lic"]),
                "--new-license", str(new_lic),
                "--output", str(req),
            ],
        )
        assert res.exit_code == 0, res.output

        req_data = json.loads(req.read_text())
        assert req_data["expires_at"] > req_data["issued_at"]

        # Author signs the request...
        auth = tmp_path / "auth.rzswap"
        sign_res = runner.invoke(
            app,
            ["sign-swap", "--request", str(req), "--private-key", str(env["priv"]),
             "--output", str(auth)],
        )
        assert sign_res.exit_code == 0, sign_res.output

        # ...and it verifies against both licenses.
        verify_res = runner.invoke(
            app,
            [
                "verify-swap", str(auth), "--public-key", str(pub),
                "--current-license", str(env["lic"]),
                "--new-license", str(new_lic),
                "--request-id", req_data["request_id"],
            ],
        )
        assert verify_res.exit_code == 0, verify_res.output

    def test_custom_request_id_preserved(self, env, tmp_path):
        req = tmp_path / "req.json"
        res = runner.invoke(
            app,
            [
                "create-swap-request",
                "--current-license", str(env["lic"]),
                "--new-license", str(env["lic"]),
                "--output", str(req),
                "--request-id", "my-custom-id-42",
            ],
        )
        assert res.exit_code == 0
        assert json.loads(req.read_text())["request_id"] == "my-custom-id-42"

    def test_non_positive_valid_minutes_rejected(self, env, tmp_path):
        res = runner.invoke(
            app,
            [
                "create-swap-request",
                "--current-license", str(env["lic"]),
                "--new-license", str(env["lic"]),
                "--output", str(tmp_path / "r.json"),
                "--valid-minutes", "0",
            ],
        )
        assert res.exit_code == 1
