"""License token validation and decoding (Task 4.5)."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import jwt

from .hwid import HardwareIdentifier
from .license_token import LicensePayload

logger = logging.getLogger("license")


class LicenseValidator:
    """Validates JWT license tokens against an RSA public key."""

    ALGORITHM = "RS256"

    def __init__(self, public_key: str):
        self.public_key = public_key

    @classmethod
    def from_file(cls, public_key_path: str) -> LicenseValidator:
        with open(public_key_path, "r") as f:
            return cls(f.read())

    # ---------- decode (no expiry / hwid checks) ----------

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode a token *without* expiry or HWID checks.

        Used by the read-only License Viewer tab.
        """
        return jwt.decode(
            token,
            self.public_key,
            algorithms=[self.ALGORITHM],
            options={"verify_exp": False},
        )

    # ---------- full validation ----------

    def validate(
        self, token: str, check_hwid: bool = True
    ) -> LicensePayload:
        """Fully validate *token*: signature, expiry, and optional HWID."""
        try:
            payload_dict = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.ALGORITHM],
            )
        except jwt.ExpiredSignatureError:
            logger.warning("License check failed: expired")
            raise ValueError("expired")
        except jwt.InvalidSignatureError:
            logger.warning("License check failed: tampered")
            raise ValueError("tampered")
        except jwt.DecodeError as exc:
            logger.warning("License check failed: decode_error (%s)", exc)
            raise ValueError("decode_error")

        payload = LicensePayload.from_dict(payload_dict)

        if check_hwid and payload.hwid != HardwareIdentifier.get_machine_id():
            logger.warning("License check failed: hwid_mismatch")
            raise ValueError("hwid_mismatch")

        logger.info(
            "License OK: client=%s  exp=%s", payload.client, payload.exp
        )
        return payload

    def validate_from_file(
        self,
        license_path: str,
        check_hwid: bool = True,
    ) -> LicensePayload:
        """Read *license_path* and validate its contents."""
        try:
            with open(license_path) as f:
                token = f.read().strip()
        except FileNotFoundError:
            logger.warning("License check failed: missing license file")
            raise ValueError("missing")

        return self.validate(token, check_hwid=check_hwid)
