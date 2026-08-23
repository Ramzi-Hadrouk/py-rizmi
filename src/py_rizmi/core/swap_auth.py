"""Core license swap authorization signing and verification logic."""
from __future__ import annotations

import base64
import json
import logging
import time
import uuid
from typing import Any, Dict, Tuple

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

from py_rizmi.core.crypto import load_private_key, load_public_key
from py_rizmi.models.swap_payload import (
    FIXED_OPERATION,
    PROTOCOL_VERSION,
    LicenseSwapPayload,
)

logger = logging.getLogger("license")


def canonicalize_payload(payload_dict: Dict[str, Any]) -> bytes:
    """Return deterministic JSON byte representation for signing.

    Uses sorted keys and no whitespace separators (',', ':'), UTF-8 encoded.
    """
    return json.dumps(payload_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")


def create_swap_request(
    current_license: str,
    new_license: str,
    request_id: str | None = None,
    valid_minutes: int = 60,
) -> LicenseSwapPayload:
    """Generate a fresh license swap authorization payload with short-lived expiration.

    *valid_minutes* must be positive -- swap authorizations are deliberately
    short-lived credentials; a non-expiring one would defeat the protocol.
    """
    if valid_minutes <= 0:
        raise ValueError(
            f"valid_minutes must be positive (got {valid_minutes}); swap "
            "authorizations are short-lived by design"
        )
    now = int(time.time())
    payload = LicenseSwapPayload(
        protocol_version=PROTOCOL_VERSION,
        operation=FIXED_OPERATION,
        request_id=request_id if request_id else str(uuid.uuid4()),
        current_license=current_license.strip(),
        new_license=new_license.strip(),
        issued_at=now,
        expires_at=now + (valid_minutes * 60),
    )
    return payload


def sign_swap_request(
    payload: LicenseSwapPayload | Dict[str, Any],
    private_key_pem: str,
    passphrase: str | None = None,
) -> Dict[str, Any]:
    """Sign payload using RSA private key (PKCS1v15 + SHA256) and return envelope dict.

    Return Envelope Structure:
    {
      "payload": { ... },
      "signature": "<base64_encoded_signature>"
    }

    Rejects payloads whose ``expires_at`` is not in the future: signing a
    request without a real expiry window would mint a perpetually-valid
    authorization, which contradicts the short-lived design of the swap
    protocol.
    """
    if isinstance(payload, LicenseSwapPayload):
        payload_dict = payload.to_dict()
    else:
        payload_dict = payload

    expires_at = int(payload_dict.get("expires_at", 0))
    if expires_at <= 0:
        raise ValueError(
            "swap authorization must have a positive expires_at; refusing to "
            "sign a non-expiring authorization"
        )

    priv_key = load_private_key(private_key_pem, password=passphrase)
    canonical_bytes = canonicalize_payload(payload_dict)

    signature_bytes = priv_key.sign(
        canonical_bytes,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )

    signature_b64 = base64.b64encode(signature_bytes).decode("utf-8")

    return {
        "payload": payload_dict,
        "signature": signature_b64,
    }


def verify_swap_authorization(
    authorization_data: Dict[str, Any] | str,
    public_key_pem: str,
    expected_current_license: str,
    expected_new_license: str,
    expected_request_id: str | None = None,
    current_time: int | None = None,
) -> Tuple[bool, str, LicenseSwapPayload | None]:
    """Verify license swap authorization signature, expiration, operation, and license binding.

    This function is the primary validation API consumed by applications (e.g. Django).
    Returns: (is_valid, error_code_or_reason, payload_object)
    """
    if isinstance(authorization_data, str):
        try:
            auth_dict = json.loads(authorization_data)
        except (json.JSONDecodeError, TypeError):
            return False, "invalid_json", None
    elif isinstance(authorization_data, dict):
        auth_dict = authorization_data
    else:
        return False, "invalid_input_type", None

    payload_raw = auth_dict.get("payload")
    sig_b64 = auth_dict.get("signature")

    if not payload_raw or not sig_b64 or not isinstance(payload_raw, dict) or not isinstance(sig_b64, str):
        return False, "malformed_authorization", None

    # 1. RSA Signature Verification FIRST -- nothing about an unauthenticated
    # envelope (its expiry state, its license bindings) may be probed or
    # trusted before authenticity is established.
    try:
        pub_key = load_public_key(public_key_pem)
        raw_sig_bytes = base64.b64decode(sig_b64, validate=True)
        canonical_bytes = canonicalize_payload(payload_raw)
        pub_key.verify(
            raw_sig_bytes,
            canonical_bytes,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except (ValueError, TypeError) as exc:
        # binascii.Error (bad base64) and unusable key material surface here.
        logger.warning("Swap authorization rejected: invalid_signature (%s)", exc)
        return False, "invalid_signature", None
    except InvalidSignature:
        return False, "invalid_signature", None
    except Exception as exc:  # malformed PEM / unsupported key type
        logger.warning("Swap authorization rejected: invalid_signature (%s)", exc)
        return False, "invalid_signature", None

    try:
        payload = LicenseSwapPayload.from_dict(payload_raw)
    except Exception:
        return False, "malformed_payload", None

    # 2. Protocol version check (signature now verified)
    if payload.protocol_version != PROTOCOL_VERSION:
        return False, "unsupported_protocol_version", None

    # 2. Fixed operation check
    if payload.operation != FIXED_OPERATION:
        return False, "invalid_operation", None

    # 3. Expiration check
    if payload.is_expired(current_time=current_time):
        return False, "authorization_expired", None

    # 4. License content match checks (exact string equality after strip)
    if payload.current_license.strip() != expected_current_license.strip():
        return False, "current_license_mismatch", None

    if payload.new_license.strip() != expected_new_license.strip():
        return False, "new_license_mismatch", None

    # 5. Request ID check (if expected_request_id provided)
    if expected_request_id and payload.request_id != expected_request_id:
        return False, "request_id_mismatch", None

    return True, "valid", payload


# Backward-compatibility aliases
create_replacement_authorization_payload = create_swap_request
sign_authorization_payload = sign_swap_request
verify_authorization = verify_swap_authorization
