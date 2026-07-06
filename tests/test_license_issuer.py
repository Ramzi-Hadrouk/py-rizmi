from src.core.license_issuer import LicenseIssuer
from src.core.license_token import LicensePayload


def test_issue_returns_jwt_string(temp_keypair, sample_payload):
    priv, _ = temp_keypair
    sample_payload.set_auto_iat()
    sample_payload.set_auto_exp(365)
    token = LicenseIssuer.from_file(str(priv)).issue(sample_payload)
    assert isinstance(token, str)
    assert token.count(".") == 2  # JWT has three dot-separated parts


def test_issue_to_file(temp_keypair, sample_payload, tmp_path):
    priv, _ = temp_keypair
    sample_payload.set_auto_iat()
    sample_payload.set_auto_exp(365)
    out = tmp_path / "license.lic"
    LicenseIssuer.from_file(str(priv)).issue_to_file(sample_payload, str(out))
    assert out.exists()
    assert out.read_text().count(".") == 2
