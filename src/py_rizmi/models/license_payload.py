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
        """Construct a payload from a (typically JWT-decoded) dictionary.

        Fields are type-checked and coerced so that a malformed token
        fails here, at the boundary, with a clear ``ValueError`` instead
        of producing confusing failures deep inside validation or GUI
        code. Unknown keys are ignored (forward compatibility).
        """
        schema_version = _require_int(data, "schema_version", default=1)
        max_clients = _require_int(data, "max_clients", default=10)
        grace_days = _require_int(data, "grace_days", default=14)
        iat = _require_int(data, "iat", default=0)
        exp = _require_int(data, "exp", default=0)

        if schema_version < 0:
            raise ValueError("schema_version must be non-negative")
        if max_clients < 0:
            raise ValueError("max_clients must be non-negative")
        if grace_days < 0:
            raise ValueError("grace_days must be non-negative")
        if iat < 0 or exp < 0:
            raise ValueError("iat/exp must be non-negative timestamps")

        client = data.get("client", "")
        license_id = data.get("license_id", "")
        hwid = data.get("hwid", "")
        mode = data.get("mode", "offline")
        server_url = data.get("server_url", "")
        for name, value in (
            ("client", client),
            ("license_id", license_id),
            ("hwid", hwid),
            ("mode", mode),
            ("server_url", server_url),
        ):
            if not isinstance(value, str):
                raise ValueError(f"{name} must be a string, got {type(value).__name__}")

        features_raw = data.get("features", [])
        if not isinstance(features_raw, (list, tuple)):
            raise ValueError(
                f"features must be a list of strings, got {type(features_raw).__name__}"
            )
        features: List[str] = []
        for f in features_raw:
            if not isinstance(f, str):
                raise ValueError("features must contain only strings")
            features.append(f)

        return cls(
            schema_version=schema_version,
            client=client,
            license_id=license_id,
            hwid=hwid,
            features=features,
            max_clients=max_clients,
            mode=mode,
            server_url=server_url,
            grace_days=grace_days,
            iat=iat,
            exp=exp,
        )

    def set_auto_iat(self) -> None:
        self.iat = int(time.time())

    def set_auto_exp(self, days: int = 365) -> None:
        self.exp = int(time.time()) + days * 86_400

    def is_expired(self) -> bool:
        """True once *exp* has passed -- regardless of any grace period.

        Note this differs from validator behavior: `LicenseValidator`
        still honors a license during its grace period (raising only
        after exp + grace_days). Use `is_in_grace()` to distinguish the
        two states.
        """
        return self.exp > 0 and int(time.time()) > self.exp

    def is_in_grace(self) -> bool:
        """True if the license is expired but still inside its grace window."""
        if self.exp <= 0 or not self.is_expired():
            return False
        effective_exp = self.exp + self.grace_days * 86_400
        return int(time.time()) <= effective_exp


def _require_int(data: Dict[str, Any], key: str, default: int) -> int:
    """Fetch *key* as an int, accepting bool-free ints and numeric strings.

    Raises ValueError for anything that is not unambiguously an integer
    (floats with fractions, bools, arbitrary objects).
    """
    value = data.get(key, default)
    if isinstance(value, bool):
        raise ValueError(f"{key} must be an integer, got bool")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise ValueError(f"{key} must be an integer, got {value!r}")
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"{key} must be an integer, got {value!r}") from None
    raise ValueError(f"{key} must be an integer, got {type(value).__name__}")
