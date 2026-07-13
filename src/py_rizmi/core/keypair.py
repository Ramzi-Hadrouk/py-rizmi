"""RSA keypair generation and management."""
from __future__ import annotations

from typing import Tuple

from .crypto import (
    generate_rsa_keypair,
    load_private_key as _load_priv,
    load_public_key as _load_pub,
    save_pem,
)


class KeyPairManager:
    """Generate, save, load, and validate RSA keypairs for JWT signing."""

    DEFAULT_KEY_SIZE = 2048
    KEY_SIZES = [2048, 3072, 4096]

    @classmethod
    def generate_keypair(
        cls, key_size: int = DEFAULT_KEY_SIZE
    ) -> Tuple[str, str]:
        """Generate a keypair and return (private_pem, public_pem) strings."""
        return generate_rsa_keypair(key_size)

    @classmethod
    def save_keypair(
        cls,
        private_path: str,
        public_path: str,
        key_size: int = DEFAULT_KEY_SIZE,
    ) -> None:
        """Generate and persist a keypair to disk."""
        import os

        private_pem, public_pem = cls.generate_keypair(key_size)
        save_pem(private_pem, private_path)
        os.chmod(private_path, 0o600)
        save_pem(public_pem, public_path)

    @staticmethod
    def load_private_key(path: str) -> str:
        with open(path, "r") as f:
            return f.read()

    @staticmethod
    def load_public_key(path: str) -> str:
        with open(path, "r") as f:
            return f.read()

    @staticmethod
    def validate_private_key(pem_string: str) -> bool:
        """Return True if *pem_string* is a well-formed RSA private key."""
        try:
            _load_priv(pem_string)
            return True
        except Exception:
            return False

    @staticmethod
    def validate_public_key(pem_string: str) -> bool:
        """Return True if *pem_string* is a well-formed RSA public key."""
        try:
            _load_pub(pem_string)
            return True
        except Exception:
            return False

    @staticmethod
    def verify_keypair(private_pem: str, public_pem: str) -> bool:
        """Return True if *public_pem* is the matching public key for *private_pem*."""
        try:
            private_key = _load_priv(private_pem)
            public_key = _load_pub(public_pem)
            priv_nums = private_key.public_key().public_numbers()
            pub_nums = public_key.public_numbers()
            return priv_nums.n == pub_nums.n and priv_nums.e == pub_nums.e
        except Exception:
            return False

    @staticmethod
    def get_key_size(pem_string: str) -> int | None:
        """Return the key size in bits, or None if the PEM is invalid."""
        try:
            if "PRIVATE KEY" in pem_string or "RSA PRIVATE KEY" in pem_string:
                key = _load_priv(pem_string)
            else:
                key = _load_pub(pem_string)
            return key.key_size
        except Exception:
            return None
