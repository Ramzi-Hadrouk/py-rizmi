"""Unit tests for license swap authorization signing and verification."""
import time
import pytest

from py_rizmi.core.keypair import KeyPairManager
from py_rizmi.core.license_issuer import LicenseIssuer
from py_rizmi.core.swap_auth import (
    canonicalize_payload,
    create_swap_request,
    sign_swap_request,
    verify_swap_authorization,
)
from py_rizmi.models.license_payload import LicensePayload
from py_rizmi.models.swap_payload import (
    FIXED_OPERATION,
    PROTOCOL_VERSION,
    LicenseSwapPayload,
)


@pytest.fixture
def rsa_keys(tmp_path):
    priv_path = tmp_path / "private.pem"
    pub_path = tmp_path / "public.pem"
    KeyPairManager.save_keypair(str(priv_path), str(pub_path))
    priv_pem = priv_path.read_text()
    pub_pem = pub_path.read_text()
    return priv_pem, pub_pem


@pytest.fixture
def sample_lic_tokens(rsa_keys, sample_payload):
    priv_pem, _ = rsa_keys
    issuer = LicenseIssuer(priv_pem)

    current_token = issuer.issue(sample_payload)

    new_payload = LicensePayload.from_dict(sample_payload.to_dict())
    new_payload.license_id = "test-002-upgraded"
    new_token = issuer.issue(new_payload)

    return current_token, new_token


def test_canonicalization_stability():
    dict1 = {"b": 2, "a": 1, "c": [1, 2]}
    dict2 = {"a": 1, "c": [1, 2], "b": 2}

    assert canonicalize_payload(dict1) == canonicalize_payload(dict2)
    assert canonicalize_payload(dict1) == b'{"a":1,"b":2,"c":[1,2]}'


def test_payload_generation(sample_lic_tokens):
    curr_lic, new_lic = sample_lic_tokens
    payload = create_swap_request(
        current_license=curr_lic,
        new_license=new_lic,
        request_id="req-12345",
        valid_minutes=15,
    )

    assert payload.protocol_version == PROTOCOL_VERSION
    assert payload.operation == FIXED_OPERATION
    assert payload.request_id == "req-12345"
    assert payload.current_license == curr_lic
    assert payload.new_license == new_lic
    assert payload.expires_at > payload.issued_at


def test_sign_and_verify_success(rsa_keys, sample_lic_tokens):
    priv_pem, pub_pem = rsa_keys
    curr_lic, new_lic = sample_lic_tokens

    payload = create_swap_request(curr_lic, new_lic, request_id="req-test-1")
    auth_envelope = sign_swap_request(payload, priv_pem)

    is_valid, reason, verified_payload = verify_swap_authorization(
        authorization_data=auth_envelope,
        public_key_pem=pub_pem,
        expected_current_license=curr_lic,
        expected_new_license=new_lic,
        expected_request_id="req-test-1",
    )

    assert is_valid is True
    assert reason == "valid"
    assert verified_payload is not None
    assert verified_payload.request_id == "req-test-1"


def test_verify_expired_authorization(rsa_keys, sample_lic_tokens):
    priv_pem, pub_pem = rsa_keys
    curr_lic, new_lic = sample_lic_tokens

    payload = create_swap_request(curr_lic, new_lic)
    payload.expires_at = int(time.time()) - 100

    auth_envelope = sign_swap_request(payload, priv_pem)

    is_valid, reason, _ = verify_swap_authorization(
        authorization_data=auth_envelope,
        public_key_pem=pub_pem,
        expected_current_license=curr_lic,
        expected_new_license=new_lic,
    )

    assert is_valid is False
    assert reason == "authorization_expired"


def test_verify_wrong_operation(rsa_keys, sample_lic_tokens):
    priv_pem, pub_pem = rsa_keys
    curr_lic, new_lic = sample_lic_tokens

    payload = create_swap_request(curr_lic, new_lic)
    payload.operation = "unauthorized_op"

    auth_envelope = sign_swap_request(payload, priv_pem)

    is_valid, reason, _ = verify_swap_authorization(
        authorization_data=auth_envelope,
        public_key_pem=pub_pem,
        expected_current_license=curr_lic,
        expected_new_license=new_lic,
    )

    assert is_valid is False
    assert reason == "invalid_operation"


def test_verify_current_license_mismatch(rsa_keys, sample_lic_tokens):
    priv_pem, pub_pem = rsa_keys
    curr_lic, new_lic = sample_lic_tokens

    payload = create_swap_request(curr_lic, new_lic)
    auth_envelope = sign_swap_request(payload, priv_pem)

    is_valid, reason, _ = verify_swap_authorization(
        authorization_data=auth_envelope,
        public_key_pem=pub_pem,
        expected_current_license="different_current_lic_token",
        expected_new_license=new_lic,
    )

    assert is_valid is False
    assert reason == "current_license_mismatch"


def test_verify_new_license_mismatch(rsa_keys, sample_lic_tokens):
    priv_pem, pub_pem = rsa_keys
    curr_lic, new_lic = sample_lic_tokens

    payload = create_swap_request(curr_lic, new_lic)
    auth_envelope = sign_swap_request(payload, priv_pem)

    is_valid, reason, _ = verify_swap_authorization(
        authorization_data=auth_envelope,
        public_key_pem=pub_pem,
        expected_current_license=curr_lic,
        expected_new_license="different_new_lic_token",
    )

    assert is_valid is False
    assert reason == "new_license_mismatch"


def test_verify_request_id_mismatch(rsa_keys, sample_lic_tokens):
    priv_pem, pub_pem = rsa_keys
    curr_lic, new_lic = sample_lic_tokens

    payload = create_swap_request(curr_lic, new_lic, request_id="uuid-req-orig")
    auth_envelope = sign_swap_request(payload, priv_pem)

    is_valid, reason, _ = verify_swap_authorization(
        authorization_data=auth_envelope,
        public_key_pem=pub_pem,
        expected_current_license=curr_lic,
        expected_new_license=new_lic,
        expected_request_id="uuid-req-different",
    )

    assert is_valid is False
    assert reason == "request_id_mismatch"


def test_verify_invalid_signature_wrong_key(rsa_keys, tmp_path, sample_lic_tokens):
    priv_pem, _ = rsa_keys
    curr_lic, new_lic = sample_lic_tokens

    priv2 = tmp_path / "priv2.pem"
    pub2 = tmp_path / "pub2.pem"
    KeyPairManager.save_keypair(str(priv2), str(pub2))

    payload = create_swap_request(curr_lic, new_lic)
    auth_envelope = sign_swap_request(payload, priv_pem)

    is_valid, reason, _ = verify_swap_authorization(
        authorization_data=auth_envelope,
        public_key_pem=pub2.read_text(),
        expected_current_license=curr_lic,
        expected_new_license=new_lic,
    )

    assert is_valid is False
    assert reason == "invalid_signature"
