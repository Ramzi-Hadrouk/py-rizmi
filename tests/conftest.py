"""Shared pytest fixtures."""
import pytest

from py_rizmi.core.keypair import KeyPairManager
from py_rizmi.models.license_payload import LicensePayload
from py_rizmi.core.hwid import HardwareIdentifier


@pytest.fixture
def temp_keypair(tmp_path):
    """Generate a fresh RSA keypair in a temp directory."""
    priv = tmp_path / "private_key.pem"
    pub = tmp_path / "public_key.pem"
    KeyPairManager.save_keypair(str(priv), str(pub))
    return priv, pub


@pytest.fixture
def sample_payload():
    """A typical LicensePayload for testing."""
    return LicensePayload(
        client="Test Customer",
        license_id="test-001",
        hwid=HardwareIdentifier.get_machine_id(),
        features=["billing", "reports"],
        max_clients=5,
        mode="offline",
        server_url="https://license.test.com/api/validate",
        grace_days=14,
    )
