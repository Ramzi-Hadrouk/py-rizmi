"""Machine fingerprint generation using OS-level machine ID.

Uses py-machineid (https://github.com/keygen-sh/py-machineid) instead of
MAC addresses (uuid.getnode()) or hostnames (platform.node()) because:

- MAC addresses can be spoofed or change across networks
- Hostnames are trivially changed by users
- The OS machine ID is tied to the OS installation, stable across reboots,
  and survives most hardware configuration changes

The OS-level machine ID is obtained from:
- Linux: /var/lib/dbus/machine-id or /etc/machine-id
- macOS: IOPlatformUUID (via ioreg)
- Windows: MachineGuid (registry) or Win32_ComputerSystemProduct.UUID
"""
import hashlib
from typing import Protocol, runtime_checkable

import machineid


@runtime_checkable
class FingerprintProvider(Protocol):
    """Protocol for pluggable machine-fingerprint backends.

    Any class implementing ``get_machine_id() -> str`` and
    ``verify(hwid: str) -> bool`` satisfies this protocol, enabling
    third-party fingerprint sources without modifying core code.
    """

    def get_machine_id(self) -> str: ...
    def verify(self, hwid: str) -> bool: ...


class MachineIdError(RuntimeError):
    """Raised when the OS-level machine identifier cannot be obtained."""


class HardwareIdentifier:
    """Generates a deterministic SHA-256 hardware fingerprint.

    The fingerprint is derived from the OS-level machine ID rather than
    MAC addresses or hostnames, providing a more stable and secure
    identifier for licensing purposes.
    """

    @staticmethod
    def get_machine_id() -> str:
        """Return SHA-256 hex digest of the OS machine identifier.

        Uses ``machineid.id()`` to obtain the platform-specific
        machine GUID, then returns its SHA-256 hash.

        Returns:
            A 64-character lowercase hex SHA-256 digest.

        Raises:
            MachineIdError: If the machine ID cannot be obtained
                (e.g. restricted container, missing system files).
        """
        try:
            raw = machineid.id()
        except machineid.MachineIdNotFound as exc:
            raise MachineIdError(
                "Unable to obtain machine identifier. "
                "The OS-level machine ID could not be read. "
                "This may indicate a restricted environment "
                "(container, VM, sandbox) or missing system files "
                "(e.g. /etc/machine-id on Linux)."
            ) from exc
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def verify(hwid: str) -> bool:
        """Return True if *hwid* matches the current machine."""
        return hwid == HardwareIdentifier.get_machine_id()
