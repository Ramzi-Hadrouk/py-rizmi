"""License token validation and decoding."""
from __future__ import annotations

import logging
from typing import Any, Dict

import jwt

from py_rizmi.core.hwid import HardwareIdentifier
from py_rizmi.models.license_payload import LicensePayload

logger = logging.getLogger("license")

ERROR_MESSAGES: dict[str, str] = {
    "missing": "License file not found.",
    "decode_error": "Token could not be decoded. Check that the public key matches the issuing private key.",
    "tampered": "License signature is invalid — the token may have been tampered with.",
    "invalid_algorithm": "License token uses an unsupported signing algorithm.",
    "unsupported_schema": "License schema version is not supported by this version of py-Rizmi.",
    "expired": "License has expired.",
    "hwid_mismatch": "Hardware fingerprint mismatch — this license is not issued for this machine.",
}


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
                options={"verify_exp": False},
            )
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

        if payload.exp != 0:
            import time
            now = int(time.time())
            effective_exp = payload.exp + (payload.grace_days * 86_400)
            if now > effective_exp:
                logger.warning("License check failed: expired (grace period ended)")
                raise ValueError("expired")
            elif now > payload.exp:
                logger.info("License is in grace period (%d days left)", (effective_exp - now) // 86_400 + 1)
                payload.in_grace_period = True

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
