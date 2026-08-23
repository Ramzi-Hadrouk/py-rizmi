"""License token validation and decoding."""
from __future__ import annotations

import logging
from typing import Any, Dict, Protocol

import jwt

from py_rizmi.core.hwid import HardwareIdentifier
from py_rizmi.core.revocation import RevocationList, REASON_REVOKED
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
    "clock_tampering": "System clock tampering detected.",
    "revoked": "License has been revoked by the issuer.",
}


class _ClockGuard(Protocol):
    def check_session_drift(self) -> Any:
        ...

    def check_and_update(self) -> Any:
        ...


class LicenseValidator:
    """Validates JWT license tokens against an RSA public key.

    Pass *revocation_list* (a signed CRL envelope from
    `core.revocation.sign_revocation_list`, dict or JSON string) to also
    reject licenses whose ``license_id`` appears on it. The list is
    verified against the same public key before use; a bad signature is
    rejected loudly (ValueError("revocation_list_invalid")) rather than
    silently ignored -- an unverifiable list must not disable revocation.
    """

    ALGORITHM = "RS256"

    def __init__(
        self,
        public_key: str,
        clock_guard: _ClockGuard | None = None,
        revocation_list: Any | None = None,
    ) -> None:
        self.public_key = public_key
        self.clock_guard = clock_guard
        self._crl: RevocationList | None = None
        if revocation_list is not None:
            self.set_revocation_list(revocation_list)

    @classmethod
    def from_file(
        cls,
        public_key_path: str,
        clock_guard: _ClockGuard | None = None,
        revocation_list: Any | None = None,
    ) -> LicenseValidator:
        with open(public_key_path, "r") as f:
            return cls(f.read(), clock_guard=clock_guard, revocation_list=revocation_list)

    def set_revocation_list(self, revocation_list: Any) -> None:
        """Install (and verify) a new signed CRL envelope at runtime."""
        from py_rizmi.core.revocation import verify_revocation_list

        ok, reason, crl = verify_revocation_list(revocation_list, self.public_key)
        if not ok or crl is None:
            logger.warning("Rejected revocation list: %s", reason)
            raise ValueError("revocation_list_invalid")
        self._crl = crl

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

        if self.clock_guard is not None:
            checks = (
                self.clock_guard.check_session_drift,
                self.clock_guard.check_and_update,
            )
            for check in checks:
                result = check()
                if not result.ok:
                    logger.warning(
                        "License check failed: clock_tampering (%s)",
                        getattr(result, "detail", ""),
                    )
                    raise ValueError("clock_tampering")

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

        if self._crl is not None and self._crl.is_revoked(payload.license_id):
            logger.warning("License check failed: revoked (%s)", payload.license_id)
            raise ValueError(REASON_REVOKED)

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
