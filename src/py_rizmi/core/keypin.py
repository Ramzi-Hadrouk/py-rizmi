"""Vendor public-key fingerprint self-check.

The vendor public key is embedded in the app as a compiled constant
(NEVER in writable storage). This module adds a cheap second gate:
the app also embeds ``sha256(public_key_pem)`` and verifies the pair at
startup. An attacker who patches the key constant but forgets the
fingerprint (or vice versa) produces a binary that refuses to run.
"""
from __future__ import annotations

import hashlib
import hmac

__all__ = ["KeyPinError", "key_fingerprint", "pin_fingerprint"]


class KeyPinError(RuntimeError):
    """The embedded public key does not match its pinned fingerprint."""


def key_fingerprint(public_key_pem: str) -> str:
    """SHA-256 hex digest of *public_key_pem* — print this once and paste
    it into your source next to the key constant."""
    return hashlib.sha256(public_key_pem.encode("utf-8")).hexdigest()


def pin_fingerprint(public_key_pem: str, expected_fingerprint_hex: str) -> None:
    """Verify the embedded key matches its pinned fingerprint; raise
    :class:`KeyPinError` on any mismatch. Call once at app startup,
    before any validation runs."""
    digest = hashlib.sha256(public_key_pem.encode("utf-8")).hexdigest()
    expected = "".join(expected_fingerprint_hex.split()).lower()
    if not hmac.compare_digest(digest, expected):
        raise KeyPinError(
            "Embedded public key does not match its pinned fingerprint. "
            "The binary may have been tampered with, or the developer "
            "updated one of (key, fingerprint) without the other."
        )
