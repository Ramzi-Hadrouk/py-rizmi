"""py-rizmi — Offline-first licensing toolkit for cryptographically signed, hardware-bound Python software protection."""


try:
    from py_rizmi._version import __version__
except ImportError:
    __version__ = "0.0.0.dev0"

from py_rizmi.core.hwid import HardwareIdentifier as MachineFingerprint
from py_rizmi.core.keypair import KeyPairManager as KeyPair
from py_rizmi.core.license_issuer import LicenseIssuer
from py_rizmi.core.license_validator import LicenseValidator
from py_rizmi.core.revocation import (
    RevocationList,
    create_revocation_list,
    sign_revocation_list,
    verify_revocation_list,
)
from py_rizmi.core.runtime_guard import LicenseWatchdog, LicenseWatchdogError
from py_rizmi.core.trial import TrialManager, TrialStatus
from py_rizmi.core.swap_auth import (
    create_replacement_authorization_payload,
    create_swap_request,
    sign_authorization_payload,
    sign_swap_request,
    verify_authorization,
    verify_swap_authorization,
)
from py_rizmi.models.license_payload import LicensePayload
from py_rizmi.models.swap_payload import LicenseSwapPayload, ReplacementAuthorizationPayload

__all__ = [
    "__version__",
    "LicenseValidator",
    "LicenseIssuer",
    "LicenseWatchdog",
    "LicenseWatchdogError",
    "RevocationList",
    "create_revocation_list",
    "sign_revocation_list",
    "verify_revocation_list",
    "TrialManager",
    "TrialStatus",
    "KeyPair",
    "MachineFingerprint",
    "LicensePayload",
    "LicenseSwapPayload",
    "ReplacementAuthorizationPayload",
    "create_swap_request",
    "create_replacement_authorization_payload",
    "sign_swap_request",
    "sign_authorization_payload",
    "verify_swap_authorization",
    "verify_authorization",
]
