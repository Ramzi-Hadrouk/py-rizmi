"""Low-level RSA and cryptographic primitives."""
from __future__ import annotations

import os
from typing import Tuple, cast

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey


def generate_rsa_keypair(
    key_size: int = 2048, passphrase: str | None = None
) -> Tuple[str, str]:
    """Generate RSA keypair, return (private_pem, public_pem) strings.

    If *passphrase* is given, the private key PEM is encrypted with it
    (AES, via cryptography's BestAvailableEncryption) instead of being
    written out in the clear.
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
    )
    encryption: serialization.KeySerializationEncryption
    if passphrase:
        encryption = serialization.BestAvailableEncryption(passphrase.encode("utf-8"))
    else:
        encryption = serialization.NoEncryption()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=encryption,
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_pem, public_pem


def load_private_key(pem: str, password: str | None = None) -> RSAPrivateKey:
    """Load a private key from PEM string, decrypting it if *password* is given."""
    pw_bytes = password.encode("utf-8") if password else None
    return cast(
        RSAPrivateKey,
        serialization.load_pem_private_key(pem.encode(), password=pw_bytes),
    )


def load_public_key(pem: str) -> RSAPublicKey:
    """Load a public key from PEM string. Returns cryptography key object."""
    return cast(RSAPublicKey, serialization.load_pem_public_key(pem.encode()))


def save_pem(pem: str, path: str) -> None:
    """Write a PEM string to disk.

    The file is created with owner-only permissions (0o600) via os.open,
    so a private key is never briefly world-readable between creation
    and a later chmod(). A best-effort chmod afterwards also tightens
    the permissions of a *pre-existing* file, whose mode the open-time
    flag does not affect.
    """
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    # O_CREAT|O_WRONLY|O_TRUNC with mode 0o600: permission bits apply at
    # file creation (subject to umask), closing the race where a key
    # exists world-readable between open() and chmod().
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(pem)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
