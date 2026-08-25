"""py-rizmi — Offline-first licensing toolkit for cryptographically signed, hardware-bound Python software protection."""


try:
    from py_rizmi._version import __version__
except ImportError:
    __version__ = "0.0.0.dev0"

from py_rizmi.core.hwid import HardwareIdentifier as MachineFingerprint
from py_rizmi.core.config import RizmiConfig
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
from py_rizmi.core.state_store import StateStore
from py_rizmi.core.license_activator import ActivationResult, LicenseActivator
from py_rizmi.core.keypin import KeyPinError, key_fingerprint, pin_fingerprint
from py_rizmi.models.license_payload import LicensePayload

__all__ = [
    "__version__",
    "RizmiConfig",
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
    "StateStore",
    "LicenseActivator",
    "ActivationResult",
    "KeyPinError",
    "key_fingerprint",
    "pin_fingerprint",
    "KeyPair",
    "MachineFingerprint",
    "LicensePayload",
]
