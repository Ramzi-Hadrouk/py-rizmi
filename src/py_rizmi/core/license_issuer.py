"""License token signing / issuance."""
from __future__ import annotations

import logging
import os

import jwt

from py_rizmi.core.crypto import load_private_key
from py_rizmi.models.license_payload import LicensePayload

logger = logging.getLogger("license")


class LicenseIssuer:
    """Signs LicensePayload objects into JWT tokens using an RSA private key."""

    ALGORITHM = "RS256"

    def __init__(self, private_key: str, passphrase: str | None = None):
        self.private_key = private_key
        self.passphrase = passphrase

    @classmethod
    def from_file(cls, private_key_path: str, passphrase: str | None = None) -> LicenseIssuer:
        with open(private_key_path, "r") as f:
            return cls(f.read(), passphrase=passphrase)

    def issue(self, payload: LicensePayload) -> str:
        """Sign *payload* and return the JWT token string."""
        signing_key = load_private_key(self.private_key, password=self.passphrase)
        token = jwt.encode(
            payload.to_dict(),
            signing_key,
            algorithm=self.ALGORITHM,
        )
        logger.info(
            "License issued: client=%s  id=%s  exp=%s",
            payload.client, payload.license_id, payload.exp,
        )
        return token

    def issue_to_file(
        self, payload: LicensePayload, output_path: str
    ) -> str:
        """Sign *payload* and write the token to *output_path*."""
        token = self.issue(payload)
        d = os.path.dirname(output_path)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(token)
        return token
