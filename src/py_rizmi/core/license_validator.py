"""License token validation and decoding."""
from __future__ import annotations

import logging
from typing import Any, Dict

import jwt

from py_rizmi.core.hwid import HardwareIdentifier
from py_rizmi.models.license_payload import LicensePayload

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

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode a token *without* expiry or HWID checks."""
        return jwt.decode(
            token,
            self.public_key,
            algorithms=[self.ALGORITHM],
            options={"verify_exp": False},
        )

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
        except jwt.InvalidAlgorithmError:
            logger.warning("License check failed: invalid_algorithm")
            raise ValueError("invalid_algorithm")
        except jwt.DecodeError as exc:
            logger.warning("License check failed: decode_error (%s)", exc)
            raise ValueError("decode_error")

        payload = LicensePayload.from_dict(payload_dict)

        if payload.schema_version != 1:
            logger.warning(f"License check failed: unsupported_schema ({payload.schema_version})")
            raise ValueError("unsupported_schema")

        if check_hwid and payload.hwid.lower() != HardwareIdentifier.get_machine_id().lower():
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
