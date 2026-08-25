"""Tests for the vendor public-key fingerprint self-check."""
from __future__ import annotations

import hashlib

import pytest

from py_rizmi.core.keypin import KeyPinError, key_fingerprint, pin_fingerprint


PEM_A = "-----BEGIN PUBLIC KEY-----\nAAAA\n-----END PUBLIC KEY-----\n"
PEM_B = "-----BEGIN PUBLIC KEY-----\nBBBB\n-----END PUBLIC KEY-----\n"


def test_key_fingerprint_is_sha256_hex() -> None:
    assert key_fingerprint(PEM_A) == hashlib.sha256(PEM_A.encode()).hexdigest()


def test_pin_accepts_matching_key() -> None:
    pin_fingerprint(PEM_A, hashlib.sha256(PEM_A.encode()).hexdigest())


def test_pin_rejects_swapped_key() -> None:
    with pytest.raises(KeyPinError, match="fingerprint"):
        pin_fingerprint(PEM_B, hashlib.sha256(PEM_A.encode()).hexdigest())


def test_pin_is_case_insensitive_on_hex() -> None:
    fp = hashlib.sha256(PEM_A.encode()).hexdigest().upper()
    pin_fingerprint(PEM_A, fp)


def test_pin_tolerates_whitespace_in_expected() -> None:
    fp = hashlib.sha256(PEM_A.encode()).hexdigest()
    pin_fingerprint(PEM_A, f" {fp}\n")
