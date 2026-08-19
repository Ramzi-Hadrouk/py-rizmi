"""Core cryptographic and fingerprint primitives."""

from py_rizmi.core.hwid import FingerprintProvider, HardwareIdentifier
from py_rizmi.core.keypair import KeyPairManager
from py_rizmi.core.license_issuer import LicenseIssuer
from py_rizmi.core.license_validator import LicenseValidator
from py_rizmi.core.swap_auth import (
    canonicalize_payload,
    create_replacement_authorization_payload,
    create_swap_request,
    sign_authorization_payload,
    sign_swap_request,
    verify_authorization,
    verify_swap_authorization,
)

__all__ = [
    "FingerprintProvider",
    "HardwareIdentifier",
    "KeyPairManager",
    "LicenseIssuer",
    "LicenseValidator",
    "canonicalize_payload",
    "create_swap_request",
    "create_replacement_authorization_payload",
    "sign_swap_request",
    "sign_authorization_payload",
    "verify_swap_authorization",
    "verify_authorization",
]
