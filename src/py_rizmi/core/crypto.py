"""Low-level RSA and cryptographic primitives."""
from __future__ import annotations

import os
from typing import Tuple, cast

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey


def generate_rsa_keypair(key_size: int = 2048) -> Tuple[str, str]:
    """Generate RSA keypair, return (private_pem, public_pem) strings."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_pem, public_pem


def load_private_key(pem: str) -> RSAPrivateKey:
    """Load a private key from PEM string. Returns cryptography key object."""
    return cast(RSAPrivateKey, serialization.load_pem_private_key(pem.encode(), password=None))


def load_public_key(pem: str) -> RSAPublicKey:
    """Load a public key from PEM string. Returns cryptography key object."""
    return cast(RSAPublicKey, serialization.load_pem_public_key(pem.encode()))


def save_pem(pem: str, path: str) -> None:
    """Write a PEM string to disk."""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w") as f:
        f.write(pem)
