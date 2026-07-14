"""Contract tests to ensure backward compatibility and schema evolution."""
import json
import base64
from pathlib import Path
from unittest.mock import patch

import pytest
import jwt
from py_rizmi.core.license_validator import LicenseValidator
from py_rizmi.core.hwid import HardwareIdentifier

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "pre_migration"


def test_pre_migration_license_loads_correctly():
    """Ensure the current LicenseValidator accepts pre-migration (Phase 1) fixtures."""
    with open(FIXTURES_DIR / "public.pem", "r") as f:
        pub_key = f.read()
    with open(FIXTURES_DIR / "license.lic", "r") as f:
        token = f.read()

    validator = LicenseValidator(pub_key)

    # We must mock the hardware ID since the license is bound to a specific HWID
    mock_hwid = "a1b2c3d4e5f60708091011121314151617181920212223242526272829303132"
    with patch.object(HardwareIdentifier, "get_machine_id", return_value=mock_hwid):
        # We pass check_hwid=True to test the HWID binding, but bypass exp checks via time patching
        # The token is fixed with iat=1700000000, exp=1800000000, so we mock time
        import time
        with patch.object(time, "time", return_value=1750000000):
            payload = validator.validate(token, check_hwid=True)
            
            assert payload.client == "Acme Corp"
            assert payload.license_id == "LIC-12345"
            assert payload.hwid == mock_hwid
            assert payload.features == ["pro", "enterprise"]
            assert payload.max_clients == 50
            assert payload.schema_version == 1


def test_schema_mismatch_raises_clear_error():
    """Ensure that future schema versions fail gracefully rather than crashing."""
    with open(FIXTURES_DIR / "public.pem", "r") as f:
        pub_key = f.read()
    with open(FIXTURES_DIR / "private.pem", "r") as f:
        priv_key = f.read()

    # Create a token with schema_version = 2
    payload_dict = {
        "schema_version": 2,
        "client": "Future",
        "license_id": "999",
        "hwid": "",
        "features": [],
        "max_clients": 1,
        "mode": "offline",
        "server_url": "",
        "grace_days": 14,
        "iat": 1700000000,
        "exp": 1800000000,
    }
    future_token = jwt.encode(payload_dict, priv_key, algorithm="RS256")
    
    validator = LicenseValidator(pub_key)
    
    # We expect a ValueError or something clear, but for now we expect a 
    # specific mismatch error. Actually, py_rizmi doesn't currently check schema_version.
    # Let's add that check in the codebase!
    with pytest.raises(ValueError, match="unsupported_schema"):
        import time
        with patch.object(time, "time", return_value=1750000000):
            validator.validate(future_token, check_hwid=False)
