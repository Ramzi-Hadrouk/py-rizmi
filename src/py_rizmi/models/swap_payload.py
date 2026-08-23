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
        """Construct payload instance from dictionary representation.

        Fields are type-checked/coerced so malformed envelopes fail here
        with a clear ``ValueError`` instead of producing confusing
        behavior during signing or verification.
        """
        protocol_version = _require_int(data, "protocol_version", PROTOCOL_VERSION)
        issued_at = _require_int(data, "issued_at", 0)
        expires_at = _require_int(data, "expires_at", 0)
        if issued_at < 0 or expires_at < 0:
            raise ValueError("issued_at/expires_at must be non-negative timestamps")

        request_id = data.get("request_id", "")
        current_license = data.get("current_license", "")
        new_license = data.get("new_license", "")
        operation = data.get("operation", FIXED_OPERATION)
        for name, value in (
            ("request_id", request_id),
            ("current_license", current_license),
            ("new_license", new_license),
            ("operation", operation),
        ):
            if not isinstance(value, str):
                raise ValueError(f"{name} must be a string, got {type(value).__name__}")

        return cls(
            protocol_version=protocol_version,
            operation=operation,
            request_id=request_id,
            current_license=current_license,
            new_license=new_license,
            issued_at=issued_at,
            expires_at=expires_at,
        )

    def is_expired(self, current_time: int | None = None) -> bool:
        """Return True if payload is past its expiration timestamp."""
        now = current_time if current_time is not None else int(time.time())
        return self.expires_at > 0 and now > self.expires_at


def _require_int(data: Dict[str, Any], key: str, default: int) -> int:
    """Fetch *key* as an int; see license_payload._require_int for rules."""
    value = data.get(key, default)
    if isinstance(value, bool):
        raise ValueError(f"{key} must be an integer, got bool")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise ValueError(f"{key} must be an integer, got {value!r}")
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"{key} must be an integer, got {value!r}") from None
    raise ValueError(f"{key} must be an integer, got {type(value).__name__}")


# Alias for backward compatibility
ReplacementAuthorizationPayload = LicenseSwapPayload
