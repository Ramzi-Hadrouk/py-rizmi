"""License token data model."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class LicensePayload:
    """Strongly-typed model for every field in the JWT payload.

    Every field is exposed as a dataclass attribute so the GUI can
    bind input widgets dynamically — nothing is hard-coded.
    """

    schema_version: int = 1
    client: str = ""
    license_id: str = ""
    hwid: str = ""
    features: List[str] = field(default_factory=list)
    max_clients: int = 10
    mode: str = "offline"
    server_url: str = ""
    grace_days: int = 14
    iat: int = 0
    exp: int = 0
    in_grace_period: bool = field(default=False, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "client": self.client,
            "license_id": self.license_id,
            "hwid": self.hwid,
            "features": list(self.features),
            "max_clients": self.max_clients,
            "mode": self.mode,
            "server_url": self.server_url,
            "grace_days": self.grace_days,
            "iat": self.iat,
            "exp": self.exp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LicensePayload:
        return cls(
            schema_version=data.get("schema_version", 1),
            client=data.get("client", ""),
            license_id=data.get("license_id", ""),
            hwid=data.get("hwid", ""),
            features=list(data.get("features", [])),
            max_clients=data.get("max_clients", 10),
            mode=data.get("mode", "offline"),
            server_url=data.get("server_url", ""),
            grace_days=data.get("grace_days", 14),
            iat=data.get("iat", 0),
            exp=data.get("exp", 0),
        )

    def set_auto_iat(self) -> None:
        self.iat = int(time.time())

    def set_auto_exp(self, days: int = 365) -> None:
        self.exp = int(time.time()) + days * 86_400

    def is_expired(self) -> bool:
        return self.exp > 0 and int(time.time()) > self.exp
