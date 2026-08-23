"""Tests for license revocation (core + validator integration + CLI)."""
from __future__ import annotations

import json
import time

import pytest
from typer.testing import CliRunner

from py_rizmi.cli.commands.license_cmd import app
from py_rizmi.core.keypair import KeyPairManager
from py_rizmi.core.license_issuer import LicenseIssuer
from py_rizmi.core.license_validator import LicenseValidator
from py_rizmi.core.revocation import (
    RevocationList,
    create_revocation_list,
    sign_revocation_list,
    verify_revocation_list,
)
from py_rizmi.models.license_payload import LicensePayload

runner = CliRunner()


@pytest.fixture
def keys(tmp_path):
    priv = tmp_path / "priv.pem"
    pub = tmp_path / "pub.pem"
    KeyPairManager.save_keypair(str(priv), str(pub))
    return priv.read_text(), pub.read_text()


@pytest.fixture
def issued_license(keys):
    priv_pem, _ = keys
    payload = LicensePayload(
        client="acme", license_id="L-TO-REVOKE", hwid="h" * 64
    )
    payload.set_auto_iat()
    payload.set_auto_exp(365)
    return LicenseIssuer(priv_pem).issue(payload)


# ─── core: create / sign / verify --------------------------------------------


class TestCreateRevocationList:
    def test_basic_fields(self):
        now = int(time.time())
        p = create_revocation_list(["A", "B"], issued_at=now)
        assert p["schema_version"] == 1
        assert p["revoked_ids"] == ["A", "B"]
        assert p["next_update"] == now + 24 * 3600

    def test_empty_list_is_valid_clean_list(self):
        p = create_revocation_list([], issued_at=1)
        assert p["revoked_ids"] == []

    def test_non_positive_next_update_hours_rejected(self):
        with pytest.raises(ValueError, match="next_update_hours"):
            create_revocation_list([], next_update_hours=0)

    def test_non_string_ids_rejected(self):
        with pytest.raises(ValueError, match="revoked_ids"):
            create_revocation_list(["ok", 42])  # type: ignore[list-item]

    def test_blank_id_rejected(self):
        with pytest.raises(ValueError, match="revoked_ids"):
            create_revocation_list(["   "])


class TestSignAndVerify:
    def test_roundtrip_valid(self, keys):
        priv_pem, pub_pem = keys
        envelope = sign_revocation_list(create_revocation_list(["X"]), priv_pem)
        ok, reason, crl = verify_revocation_list(envelope, pub_pem)
        assert ok is True
        assert reason == "valid"
        assert crl is not None and crl.is_revoked("X")
        assert not crl.is_stale

    def test_json_string_input(self, keys):
        priv_pem, pub_pem = keys
        envelope = sign_revocation_list(create_revocation_list(["X"]), priv_pem)
        ok, reason, crl = verify_revocation_list(json.dumps(envelope), pub_pem)
        assert ok is True and reason == "valid"

    def test_tampered_payload_rejected_as_signature(self, keys):
        priv_pem, pub_pem = keys
        envelope = sign_revocation_list(create_revocation_list(["X"]), priv_pem)
        envelope["payload"]["revoked_ids"].append("INJECTED")
        ok, reason, crl = verify_revocation_list(envelope, pub_pem)
        assert ok is False
        assert reason == "invalid_signature"
        assert crl is None

    def test_wrong_key_rejected(self, keys, tmp_path):
        priv_pem, _ = keys
        priv2 = tmp_path / "p2.pem"
        pub2 = tmp_path / "u2.pem"
        KeyPairManager.save_keypair(str(priv2), str(pub2))
        envelope = sign_revocation_list(create_revocation_list(["X"]), priv_pem)
        ok, reason, _ = verify_revocation_list(envelope, pub2.read_text())
        assert ok is False and reason == "invalid_signature"

    def test_invalid_base64_signature(self, keys):
        _, pub_pem = keys
        envelope = {"payload": {"schema_version": 1, "revoked_ids": []}, "signature": "!!!"}
        ok, reason, _ = verify_revocation_list(envelope, pub_pem)
        assert ok is False and reason == "invalid_signature"

    def test_semantics_not_probed_before_signature(self, keys):
        """Bad schema + bad signature must report invalid_signature, not schema."""
        _, pub_pem = keys
        envelope = {
            "payload": {"schema_version": 999, "revoked_ids": "not-a-list"},
            "signature": "AAAA",
        }
        ok, reason, _ = verify_revocation_list(envelope, pub_pem)
        assert ok is False and reason == "invalid_signature"

    def test_bad_schema_with_valid_signature_rejected(self, keys):
        priv_pem, pub_pem = keys
        payload = create_revocation_list(["X"])
        payload["schema_version"] = 99
        # Sign the mutated payload directly through the low-level signer so
        # only verify()'s schema check is under test.
        from py_rizmi.core.revocation import canonicalize_crl

        import base64 as _b64

        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        from py_rizmi.core.crypto import load_private_key

        key = load_private_key(priv_pem)
        sig = key.sign(canonicalize_crl(payload), padding.PKCS1v15(), hashes.SHA256())
        envelope = {
            "payload": payload,
            "signature": _b64.b64encode(sig).decode("ascii"),
        }
        ok, reason, _ = verify_revocation_list(envelope, pub_pem)
        assert ok is False and reason == "unsupported_schema"

    def test_malformed_envelopes(self, keys):
        _, pub_pem = keys
        for bad in ["{not json", 42, None, {}, {"payload": {}}, {"signature": "x"}]:
            ok, reason, crl = verify_revocation_list(bad, pub_pem)  # type: ignore[arg-type]
            assert ok is False and crl is None

    def test_sign_rejects_bad_schema_and_payload_shapes(self, keys):
        priv_pem, _ = keys
        with pytest.raises(ValueError, match="schema_version"):
            sign_revocation_list({"schema_version": 2, "revoked_ids": []}, priv_pem)
        with pytest.raises(ValueError, match="revoked_ids"):
            sign_revocation_list({"schema_version": 1, "revoked_ids": "x"}, priv_pem)


class TestStaleness:
    def test_past_next_update_reports_stale_but_trusted(self, keys):
        priv_pem, pub_pem = keys
        payload = create_revocation_list(["X"], next_update_hours=1, issued_at=1)
        # issued_at=1 -> next_update ~1970; still signable/verifiable.
        envelope = sign_revocation_list(payload, priv_pem)
        ok, reason, crl = verify_revocation_list(envelope, pub_pem)
        assert ok is True
        assert reason == "stale_next_update"
        assert crl is not None and crl.is_stale and crl.is_revoked("X")


# ─── validator integration ----------------------------------------------------


class TestValidatorIntegration:
    def test_revoked_license_fails_validation(self, keys, issued_license):
        _, pub_pem = keys
        crl_env = sign_revocation_list(
            create_revocation_list(["L-TO-REVOKE"]), keys[0]
        )
        validator = LicenseValidator(pub_pem, revocation_list=crl_env)
        with pytest.raises(ValueError, match="revoked"):
            validator.validate(issued_license, check_hwid=False)

    def test_unrelated_license_passes(self, keys, issued_license):
        _, pub_pem = keys
        crl_env = sign_revocation_list(
            create_revocation_list(["SOME-OTHER-ID"]), keys[0]
        )
        validator = LicenseValidator(pub_pem, revocation_list=crl_env)
        payload = validator.validate(issued_license, check_hwid=False)
        assert payload.license_id == "L-TO-REVOKE"

    def test_no_crl_means_no_check(self, keys, issued_license):
        _, pub_pem = keys
        validator = LicenseValidator(pub_pem)
        payload = validator.validate(issued_license, check_hwid=False)
        assert payload.client == "acme"

    def test_invalid_crl_is_loud_error_not_silent_bypass(self, keys, issued_license):
        """An unverifiable list must disable validation entirely (fail closed)."""
        _, pub_pem = keys
        forged = {"payload": {"schema_version": 1, "revoked_ids": [], "issued_at": 0,
                              "next_update": 0}, "signature": "AAAA"}
        with pytest.raises(ValueError, match="revocation_list_invalid"):
            LicenseValidator(pub_pem, revocation_list=forged)

    def test_runtime_crl_update_can_revoke_running_app(self, keys, issued_license):
        """set_revocation_list lets a long-running app start clean and be
        revoked later -- pairs with LicenseWatchdog's periodic checks."""
        priv_pem, pub_pem = keys
        validator = LicenseValidator(pub_pem)
        assert validator.validate(issued_license, check_hwid=False) is not None

        crl_env = sign_revocation_list(
            create_revocation_list(["L-TO-REVOKE"]), priv_pem
        )
        validator.set_revocation_list(crl_env)
        with pytest.raises(ValueError, match="revoked"):
            validator.validate(issued_license, check_hwid=False)


# ─── CLI -----------------------------------------------------------------------


class TestRevokeCli:
    def test_revoke_publishes_signed_list(self, keys, tmp_path):
        priv_path = tmp_path / "priv.pem"
        priv_path.write_text(keys[0])
        out = tmp_path / "crl.json"

        res = runner.invoke(
            app,
            ["revoke", "L-001", "L-002", "--private-key", str(priv_path),
             "--output", str(out)],
        )
        assert res.exit_code == 0, res.output
        envelope = json.loads(out.read_text())

        ok, reason, crl = verify_revocation_list(envelope, keys[1])
        assert ok is True and reason == "valid"
        assert crl is not None
        assert crl.revoked_ids == ["L-001", "L-002"]

    def test_revoke_empty_list_for_unrevoking(self, keys, tmp_path):
        priv_path = tmp_path / "priv.pem"
        priv_path.write_text(keys[0])
        out = tmp_path / "clean.json"
        res = runner.invoke(app, ["revoke", "--private-key", str(priv_path), "--output", str(out)])
        assert res.exit_code == 0, res.output
        _, _, crl = verify_revocation_list(json.loads(out.read_text()), keys[1])
        assert crl is not None and crl.revoked_ids == []

    def test_revoke_missing_key_fails(self, tmp_path):
        res = runner.invoke(
            app,
            ["revoke", "L-1", "--private-key", str(tmp_path / "nope.pem"),
             "--output", str(tmp_path / "c.json")],
        )
        assert res.exit_code == 1

    def test_revoke_bad_next_update_hours(self, keys, tmp_path):
        priv_path = tmp_path / "priv.pem"
        priv_path.write_text(keys[0])
        res = runner.invoke(
            app,
            ["revoke", "L-1", "--private-key", str(priv_path),
             "--next-update-hours", "0", "--output", str(tmp_path / "c.json")],
        )
        assert res.exit_code == 1


class TestRevocationListModel:
    def test_is_revoked_and_stale_flags(self):
        crl = RevocationList(revoked_ids=["A"], issued_at=1, next_update=2)
        assert crl.is_revoked("A") and not crl.is_revoked("B")
        assert crl.is_stale
        fresh = RevocationList(revoked_ids=[], issued_at=0,
                               next_update=int(time.time()) + 3600)
        assert not fresh.is_stale
