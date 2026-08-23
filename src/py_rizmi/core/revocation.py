"""License revocation via short-lived, RSA-signed revocation lists (CRL).

A hardware-bound, signed license cannot be forged -- but a license file
can be *leaked* (copied together with its machine binding being spoofed,
or before binding, or by an insider). Key rotation fixes that only at
enormous operational cost. A revocation list is the pragmatic middle
ground: the author publishes a signed list of revoked ``license_id``s;
validators reject any license whose id appears on it.

Design (mirrors the swap protocol envelope):

- The list is a plain JSON envelope ``{"payload": {...}, "signature":
  b64}`` signed with the SAME RSA private key that signs licenses
  (PKCS1v15 + SHA256 over canonical JSON).
- ``next_update`` marks when the author will publish a fresh list. It is
  ADVISORY: verification does not fail past that point (an offline
  machine must keep working with the last known list), but the returned
  ``stale`` flag lets online integrations refuse stale lists.
- Verification is signature-FIRST: nothing about an unauthenticated
  list is parsed or trusted (same hardening as `core.swap_auth`).
- An empty revoked list is fine -- publishing a fresh "nothing revoked"
  list is how you UN-revoke.

Usage::

    # Author side
    env = sign_revocation_list(
        create_revocation_list(["L-LEAKED-001"]), private_pem)
    # publish env (e.g. crl.json) to clients

    # Validator side
    validator = LicenseValidator(pub_pem, revocation_list=envelope)
    validator.validate(token)   # raises ValueError("revoked")
"""
from __future__ import annotations

import base64
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from py_rizmi.core.crypto import load_private_key, load_public_key

logger = logging.getLogger("license")

CRL_SCHEMA_VERSION = 1

REASON_REVOKED = "revoked"


def canonicalize_crl(payload_dict: Dict[str, Any]) -> bytes:
    """Deterministic JSON bytes for signing (sorted keys, tight separators)."""
    return json.dumps(payload_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass
class RevocationList:
    """Verified contents of a revocation-list envelope."""

    revoked_ids: List[str] = field(default_factory=list)
    issued_at: int = 0
    next_update: int = 0

    def is_revoked(self, license_id: str) -> bool:
        return license_id in self.revoked_ids

    @property
    def is_stale(self) -> bool:
        """True once *next_update* has passed (advisory only)."""
        return self.next_update > 0 and int(time.time()) > self.next_update


def create_revocation_list(
    revoked_ids: List[str],
    *,
    next_update_hours: int = 24,
    issued_at: Optional[int] = None,
) -> Dict[str, Any]:
    """Build an unsigned CRL payload dict.

    *next_update_hours* sets the advisory refresh horizon. Pass an empty
    *revoked_ids* list to publish a clean list (un-revoking everything).
    """
    if next_update_hours <= 0:
        raise ValueError("next_update_hours must be positive")
    now = int(time.time()) if issued_at is None else issued_at
    ids = list(revoked_ids)
    for rid in ids:
        if not isinstance(rid, str) or not rid.strip():
            raise ValueError("revoked_ids must contain non-empty strings")
    return {
        "schema_version": CRL_SCHEMA_VERSION,
        "revoked_ids": ids,
        "issued_at": now,
        "next_update": now + next_update_hours * 3600,
    }


def sign_revocation_list(
    payload: Dict[str, Any],
    private_key_pem: str,
    passphrase: str | None = None,
) -> Dict[str, Any]:
    """Sign a CRL payload; returns the ``{"payload", "signature"}`` envelope."""
    schema_version = payload.get("schema_version")
    if schema_version != CRL_SCHEMA_VERSION:
        raise ValueError(f"unsupported CRL schema_version: {schema_version!r}")
    revoked_ids = payload.get("revoked_ids")
    if not isinstance(revoked_ids, list):
        raise ValueError("revoked_ids must be a list")

    key = load_private_key(private_key_pem, password=passphrase)
    signature = key.sign(
        canonicalize_crl(payload),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return {
        "payload": payload,
        "signature": base64.b64encode(signature).decode("ascii"),
    }


def verify_revocation_list(
    authorization_data: Dict[str, Any] | str,
    public_key_pem: str,
    current_time: int | None = None,
) -> Tuple[bool, str, Optional[RevocationList]]:
    """Verify a signed CRL envelope. Signature FIRST, semantics after.

    Returns ``(ok, reason, crl)``. ``reason`` is ``"valid"`` for a good
    current list or ``"stale_next_update"`` for a good but past-due list
    (still trusted -- advisory staleness only); anything else is a
    rejection code with ``crl=None``.
    """
    if isinstance(authorization_data, str):
        try:
            envelope = json.loads(authorization_data)
        except (json.JSONDecodeError, TypeError):
            return False, "invalid_json", None
    elif isinstance(authorization_data, dict):
        envelope = authorization_data
    else:
        return False, "invalid_input_type", None

    payload_raw = envelope.get("payload")
    sig_b64 = envelope.get("signature")
    if (
        not isinstance(payload_raw, dict)
        or not isinstance(sig_b64, str)
        or not payload_raw
        or not sig_b64
    ):
        return False, "malformed_authorization", None

    # 1. Signature first -- reject before parsing/trusting anything.
    try:
        pub_key = load_public_key(public_key_pem)
        raw_sig = base64.b64decode(sig_b64, validate=True)
        pub_key.verify(
            raw_sig,
            canonicalize_crl(payload_raw),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except (InvalidSignature, ValueError, TypeError) as exc:
        logger.warning("Revocation list rejected: invalid_signature (%s)", exc)
        return False, "invalid_signature", None

    # 2. Semantics on the authenticated payload.
    schema_version = payload_raw.get("schema_version")
    if schema_version != CRL_SCHEMA_VERSION:
        return False, "unsupported_schema", None
    revoked_ids = payload_raw.get("revoked_ids")
    issued_at = payload_raw.get("issued_at", 0)
    next_update = payload_raw.get("next_update", 0)
    if not isinstance(revoked_ids, list) or not all(
        isinstance(r, str) for r in revoked_ids
    ):
        return False, "malformed_payload", None
    if not isinstance(issued_at, int) or not isinstance(next_update, int):
        return False, "malformed_payload", None

    crl = RevocationList(
        revoked_ids=list(revoked_ids),
        issued_at=issued_at,
        next_update=next_update,
    )
    now = int(time.time()) if current_time is None else current_time
    if next_update > 0 and now > next_update:
        logger.info("Revocation list is past its next_update (%d)", next_update)
        return True, "stale_next_update", crl
    return True, "valid", crl
