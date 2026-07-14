"""Regression test for Issue #42: HWID case sensitivity.

HWIDs are SHA-256 hashes (hex strings). Some users manually copy-pasted them
in uppercase, causing valid licenses to fail validation because the string
comparison was case-sensitive. The validator must compare HWIDs case-insensitively.
"""
from __future__ import annotations

from unittest.mock import patch

from py_rizmi.core.hwid import HardwareIdentifier
from py_rizmi.core.license_issuer import LicenseIssuer
from py_rizmi.core.license_validator import LicenseValidator
from py_rizmi.models.license_payload import LicensePayload


def test_hwid_case_sensitivity(tmp_path):
    """Validator must accept an uppercase HWID if it matches the machine's lowercase HWID."""
    # 1. Setup keys and issuer
    from py_rizmi.core.keypair import KeyPairManager
    priv, pub = KeyPairManager.generate_keypair(2048)
    issuer = LicenseIssuer(priv)
    validator = LicenseValidator(pub)

    # 2. Mock the machine ID to be lowercase hex
    machine_id = "a1b2c3d4e5f60708091011121314151617181920212223242526272829303132"
    with patch.object(HardwareIdentifier, "get_machine_id", return_value=machine_id):
        # 3. Issue a license using the UPPERCASE version of the same HWID
        payload = LicensePayload(client="Test", license_id="123", hwid=machine_id.upper())
        payload.set_auto_iat()
        payload.set_auto_exp()
        token = issuer.issue(payload)

        # 4. Validation must succeed (it should do a case-insensitive comparison)
        decoded = validator.validate(token, check_hwid=True)
        assert decoded.hwid.lower() == machine_id.lower()
