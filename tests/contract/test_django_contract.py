"""Integration contract tests verifying Django Phase 2 validation interface against py-rizmi."""
import json
import pytest

from py_rizmi.core.keypair import KeyPairManager
from py_rizmi.core.license_issuer import LicenseIssuer
from py_rizmi.core.swap_auth import (
    create_swap_request,
    sign_swap_request,
    verify_swap_authorization,
)
from py_rizmi.models.license_payload import LicensePayload


@pytest.fixture
def keys(tmp_path):
    priv_p = tmp_path / "priv.pem"
    pub_p = tmp_path / "pub.pem"
    KeyPairManager.save_keypair(str(priv_p), str(pub_p))
    return priv_p.read_text(), pub_p.read_text()


@pytest.fixture
def tokens(keys, sample_payload):
    priv_pem, _ = keys
    issuer = LicenseIssuer(priv_pem)

    t1 = issuer.issue(sample_payload)
    p2 = LicensePayload.from_dict(sample_payload.to_dict())
    p2.license_id = "contract-test-license-2"
    t2 = issuer.issue(p2)

    return t1, t2


def test_django_contract_verify_dict_and_string_inputs(keys, tokens):
    priv_pem, pub_pem = keys
    curr_lic, new_lic = tokens

    req_id = "django-req-uuid-9999"
    payload = create_swap_request(
        current_license=curr_lic,
        new_license=new_lic,
        request_id=req_id,
        valid_minutes=30,
    )
    auth_envelope = sign_swap_request(payload, priv_pem)

    # 1. Test verification passing dict (as Django deserializes body)
    valid_dict, reason_dict, verified_p = verify_swap_authorization(
        authorization_data=auth_envelope,
        public_key_pem=pub_pem,
        expected_current_license=curr_lic,
        expected_new_license=new_lic,
        expected_request_id=req_id,
    )
    assert valid_dict is True
    assert reason_dict == "valid"
    assert verified_p is not None
    assert verified_p.request_id == req_id

    # 2. Test verification passing JSON string directly
    raw_json_str = json.dumps(auth_envelope)
    valid_str, reason_str, verified_p_str = verify_swap_authorization(
        authorization_data=raw_json_str,
        public_key_pem=pub_pem,
        expected_current_license=curr_lic,
        expected_new_license=new_lic,
        expected_request_id=req_id,
    )
    assert valid_str is True
    assert reason_str == "valid"
    assert verified_p_str is not None
    assert verified_p_str.request_id == req_id


def test_django_contract_rejection_on_tampered_payload(keys, tokens):
    priv_pem, pub_pem = keys
    curr_lic, new_lic = tokens

    payload = create_swap_request(curr_lic, new_lic)
    auth_envelope = sign_swap_request(payload, priv_pem)

    # Tamper with the new_license payload inside the authorization dictionary
    tampered_envelope = json.loads(json.dumps(auth_envelope))
    tampered_envelope["payload"]["new_license"] = "hacked_license_token"

    valid, reason, _ = verify_swap_authorization(
        authorization_data=tampered_envelope,
        public_key_pem=pub_pem,
        expected_current_license=curr_lic,
        expected_new_license="hacked_license_token",  # Even if expected matches tampered
    )

    # Signature must fail because payload canonical bytes were altered after signing
    assert valid is False
    assert reason == "invalid_signature"
