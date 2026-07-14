"""Integration property tests ensuring robust issuance and validation."""
import json
import base64
import time
from unittest.mock import patch

import pytest
from hypothesis import given, strategies as st
import jwt

from py_rizmi.core.keypair import KeyPairManager
from py_rizmi.core.license_issuer import LicenseIssuer
from py_rizmi.core.license_validator import LicenseValidator
from py_rizmi.models.license_payload import LicensePayload
from py_rizmi.core.hwid import HardwareIdentifier

# Generate a single static keypair for the property tests to avoid huge overhead
# per generated example.
_PRIV, _PUB = KeyPairManager.generate_keypair(2048)
ISSUER = LicenseIssuer(_PRIV)
VALIDATOR = LicenseValidator(_PUB)

def mock_hwid():
    return "a1b2c3d4e5f60708091011121314151617181920212223242526272829303132"

@given(
    client=st.text(min_size=1, max_size=100),
    license_id=st.text(min_size=1, max_size=50),
    hwid=st.text(min_size=0, max_size=100),
    features=st.lists(st.text(min_size=1, max_size=20), max_size=10),
    max_clients=st.integers(min_value=1, max_value=10000),
)
def test_issue_then_validate_roundtrip(client, license_id, hwid, features, max_clients):
    """Property test: issuing and then validating a payload must return an identical payload."""
    payload = LicensePayload(
        client=client,
        license_id=license_id,
        hwid=hwid,
        features=features,
        max_clients=max_clients,
    )
    payload.set_auto_iat()
    payload.set_auto_exp(days=30)
    
    token = ISSUER.issue(payload)
    
    with patch.object(HardwareIdentifier, "get_machine_id", return_value=hwid):
        # Decode and validate
        decoded = VALIDATOR.validate(token, check_hwid=bool(hwid))
        
        assert decoded.client == client
        assert decoded.license_id == license_id
        assert decoded.hwid == hwid
        assert decoded.features == features
        assert decoded.max_clients == max_clients
        assert decoded.schema_version == 1

@given(
    mutation_index=st.integers(min_value=10, max_value=200) # mutate somewhere in the base64 output
)
def test_single_bit_mutation_fails(mutation_index):
    """Property test: any single character mutation of a signed token fails validation."""
    payload = LicensePayload(
        client="Test",
        license_id="123",
        hwid="hash",
    )
    payload.set_auto_iat()
    payload.set_auto_exp(days=30)
    
    token = ISSUER.issue(payload)
    
    # Force mutation index to be within token length
    idx = mutation_index % len(token)
    
    # Mutate a character (if it's 'a', make it 'b', etc.)
    char = token[idx]
    mutated_char = chr((ord(char) + 1) % 128)
    if mutated_char == char:
        mutated_char = 'X'
        
    mutated_token = token[:idx] + mutated_char + token[idx+1:]
    
    with pytest.raises(ValueError, match="tampered|decode_error|invalid_algorithm"):
        VALIDATOR.validate(mutated_token, check_hwid=False)
