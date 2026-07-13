"""py-rizmi — Offline RSA-signed license management."""

try:
    from py_rizmi._version import __version__
except ImportError:
    __version__ = "0.0.0.dev0"

from py_rizmi.core.hwid import HardwareIdentifier as MachineFingerprint
from py_rizmi.core.keypair import KeyPairManager as KeyPair
from py_rizmi.core.license_issuer import LicenseIssuer
from py_rizmi.core.license_validator import LicenseValidator
from py_rizmi.models.license_payload import LicensePayload

__all__ = [
    "__version__",
    "LicenseValidator",
    "LicenseIssuer",
    "KeyPair",
    "MachineFingerprint",
    "LicensePayload",
]
