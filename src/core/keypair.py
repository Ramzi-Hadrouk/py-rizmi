"""RSA keypair generation and management (Task 4.2)."""
from __future__ import annotations

import os
from typing import Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class KeyPairManager:
    """Generate, save, load, and validate RSA keypairs for JWT signing."""

    DEFAULT_KEY_SIZE = 2048
    KEY_SIZES = [2048, 3072, 4096]

    # ---------- generation ----------

    @classmethod
    def generate_keypair(
        cls, key_size: int = DEFAULT_KEY_SIZE
    ) -> Tuple[str, str]:
        """Generate a keypair and return (private_pem, public_pem) strings."""
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

    @classmethod
    def save_keypair(
        cls,
        private_path: str,
        public_path: str,
        key_size: int = DEFAULT_KEY_SIZE,
    ) -> None:
        """Generate and persist a keypair to disk."""
        private_pem, public_pem = cls.generate_keypair(key_size)

        for p in (private_path, public_path):
            d = os.path.dirname(p)
            if d:
                os.makedirs(d, exist_ok=True)

        with open(private_path, "w") as f:
            f.write(private_pem)
        os.chmod(private_path, 0o600)

        with open(public_path, "w") as f:
            f.write(public_pem)

    # ---------- load ----------

    @staticmethod
    def load_private_key(path: str) -> str:
        with open(path, "r") as f:
            return f.read()

    @staticmethod
    def load_public_key(path: str) -> str:
        with open(path, "r") as f:
            return f.read()

    # ---------- validation ----------

    @staticmethod
    def validate_private_key(pem_string: str) -> bool:
        """Return True if *pem_string* is a well-formed RSA private key."""
        try:
            serialization.load_pem_private_key(
                pem_string.encode(), password=None
            )
            return True
        except Exception:
            return False

    @staticmethod
    def validate_public_key(pem_string: str) -> bool:
        """Return True if *pem_string* is a well-formed RSA public key."""
        try:
            serialization.load_pem_public_key(pem_string.encode())
            return True
        except Exception:
            return False

    @staticmethod
    def verify_keypair(private_pem: str, public_pem: str) -> bool:
        """Return True if *public_pem* is the matching public key for *private_pem*.

        Both PEMs must be valid RSA keys. Compares the modulus (n) and
        public exponent (e) of the private key's derived public key against
        the provided public key.
        """
        try:
            private_key = serialization.load_pem_private_key(
                private_pem.encode(), password=None
            )
            public_key = serialization.load_pem_public_key(
                public_pem.encode()
            )
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
                key = serialization.load_pem_private_key(
                    pem_string.encode(), password=None
                )
            else:
                key = serialization.load_pem_public_key(pem_string.encode())
            return key.key_size
        except Exception:
            return None
