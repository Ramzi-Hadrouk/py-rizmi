import time
import pytest

from py_rizmi.core.license_issuer import LicenseIssuer
from py_rizmi.core.license_validator import LicenseValidator


def _make_token(priv_path, payload):
    payload.set_auto_iat()
    payload.set_auto_exp(365)
    return LicenseIssuer.from_file(str(priv_path)).issue(payload)


def test_validate_valid(temp_keypair, sample_payload):
    priv, pub = temp_keypair
    token = _make_token(priv, sample_payload)
    result = LicenseValidator.from_file(str(pub)).validate(token)
    assert result.client == sample_payload.client


def test_validate_expired(temp_keypair, sample_payload):
    priv, pub = temp_keypair
    sample_payload.iat = int(time.time()) - 1000
    sample_payload.exp = int(time.time()) - 100
    sample_payload.grace_days = 0
    token = LicenseIssuer.from_file(str(priv)).issue(sample_payload)
    with pytest.raises(ValueError, match="expired"):
        LicenseValidator.from_file(str(pub)).validate(token, check_hwid=False)


def test_validate_grace_period_valid(temp_keypair, sample_payload):
    priv, pub = temp_keypair
    now = int(time.time())
    sample_payload.iat = now - 1000
    sample_payload.exp = now - 86400  # Expired 1 day ago
    sample_payload.grace_days = 2     # Grace period is 2 days
    token = LicenseIssuer.from_file(str(priv)).issue(sample_payload)
    
    result = LicenseValidator.from_file(str(pub)).validate(token, check_hwid=False)
    assert result.in_grace_period is True


def test_validate_grace_period_expired(temp_keypair, sample_payload):
    priv, pub = temp_keypair
    now = int(time.time())
    sample_payload.iat = now - 1000
    sample_payload.exp = now - (3 * 86400)  # Expired 3 days ago
    sample_payload.grace_days = 2           # Grace period was 2 days
    token = LicenseIssuer.from_file(str(priv)).issue(sample_payload)
    
    with pytest.raises(ValueError, match="expired"):
        LicenseValidator.from_file(str(pub)).validate(token, check_hwid=False)


def test_validate_tampered(temp_keypair, sample_payload):
    priv, pub = temp_keypair
    token = _make_token(priv, sample_payload)
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(ValueError):
        LicenseValidator.from_file(str(pub)).validate(tampered, check_hwid=False)


def test_validate_hwid_mismatch(temp_keypair, sample_payload):
    priv, pub = temp_keypair
    sample_payload.hwid = "wrong"
    token = _make_token(priv, sample_payload)
    with pytest.raises(ValueError, match="hwid_mismatch"):
        LicenseValidator.from_file(str(pub)).validate(token, check_hwid=True)


def test_validate_hwid_ok_when_disabled(temp_keypair, sample_payload):
    priv, pub = temp_keypair
    sample_payload.hwid = "wrong"
    token = _make_token(priv, sample_payload)
    result = LicenseValidator.from_file(str(pub)).validate(token, check_hwid=False)
    assert result.hwid == "wrong"


def test_decode_token_no_checks(temp_keypair, sample_payload):
    priv, pub = temp_keypair
    sample_payload.hwid = "any"
    sample_payload.iat = int(time.time()) - 999_999
    sample_payload.exp = int(time.time()) - 999_000  # long expired
    token = LicenseIssuer.from_file(str(priv)).issue(sample_payload)
    decoded = LicenseValidator.from_file(str(pub)).decode_token(token)
    assert decoded["client"] == sample_payload.client


def test_validate_from_file(temp_keypair, sample_payload, tmp_path):
    priv, pub = temp_keypair
    token = _make_token(priv, sample_payload)
    lic = tmp_path / "license.lic"
    lic.write_text(token)
    result = LicenseValidator.from_file(str(pub)).validate_from_file(str(lic))
    assert result.client == sample_payload.client


def test_validate_missing_file(temp_keypair, tmp_path):
    _, pub = temp_keypair
    with pytest.raises(ValueError, match="missing"):
        LicenseValidator.from_file(str(pub)).validate_from_file(
            str(tmp_path / "nope.lic")
        )
