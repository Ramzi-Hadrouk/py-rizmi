"""Machine fingerprint generation (Task 4.3)."""
import hashlib
import platform
import uuid


class HardwareIdentifier:
    """Generates a deterministic SHA-256 hardware fingerprint."""

    @staticmethod
    def get_raw_fingerprint() -> str:
        """Return the raw, pre-hash fingerprint string."""
        mac = uuid.getnode()
        node = platform.node()
        system = platform.system()
        return f"{mac}-{node}-{system}"

    @staticmethod
    def get_machine_id() -> str:
        """Return SHA-256 hex digest of the machine fingerprint."""
        raw = HardwareIdentifier.get_raw_fingerprint()
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def verify(hwid: str) -> bool:
        """Return True if *hwid* matches the current machine."""
        return hwid == HardwareIdentifier.get_machine_id()
