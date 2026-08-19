"""Data model for license swap payloads."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

PROTOCOL_VERSION = 1
FIXED_OPERATION = "replace_license"


@dataclass
class LicenseSwapPayload:
    """Strongly-typed model for license swap authorization payloads."""

    protocol_version: int = PROTOCOL_VERSION
    operation: str = FIXED_OPERATION
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    current_license: str = ""
    new_license: str = ""
    issued_at: int = 0
    expires_at: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert payload into a dictionary for JSON serialization."""
        return {
            "protocol_version": self.protocol_version,
            "operation": self.operation,
            "request_id": self.request_id,
            "current_license": self.current_license,
            "new_license": self.new_license,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LicenseSwapPayload:
        """Construct payload instance from dictionary representation."""
        return cls(
            protocol_version=int(data.get("protocol_version", PROTOCOL_VERSION)),
            operation=str(data.get("operation", FIXED_OPERATION)),
            request_id=str(data.get("request_id", "")),
            current_license=str(data.get("current_license", "")),
            new_license=str(data.get("new_license", "")),
            issued_at=int(data.get("issued_at", 0)),
            expires_at=int(data.get("expires_at", 0)),
        )

    def is_expired(self, current_time: int | None = None) -> bool:
        """Return True if payload is past its expiration timestamp."""
        now = current_time if current_time is not None else int(time.time())
        return self.expires_at > 0 and now > self.expires_at


# Alias for backward compatibility
ReplacementAuthorizationPayload = LicenseSwapPayload
