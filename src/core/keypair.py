"""RSA keypair generation and management (Task 4.2)."""
import os
from typing import Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class KeyPairManager:
    """Generate, save, and load RSA keypairs for JWT signing."""

    DEFAULT_KEY_SIZE = 2048

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

    @staticmethod
    def load_private_key(path: str) -> str:
        with open(path, "r") as f:
            return f.read()

    @staticmethod
    def load_public_key(path: str) -> str:
        with open(path, "r") as f:
            return f.read()
