"""Centralized configuration for py-rizmi licensing components.

One immutable, validated object holding every tunable a developer
needs: trial length, watchdog re-check interval (1 min, 1 h, 2 h --
anything), HWID checking, clock tolerance, grace period, issuance
defaults, swap/CRL horizons, and naming.

Design rules
------------
- FROZEN: instances are immutable after construction. The watchdog runs
  a background thread; shared mutable config would be a race.
- VALIDATED at the boundary: every constraint is enforced once, here,
  in ``__post_init__`` -- consumers never re-check.
- BACKWARD COMPATIBLE: existing constructor parameters on
  LicenseWatchdog / TrialManager / etc. keep working and take precedence
  when passed explicitly. ``from_config()`` is additive.
- JSON round-trip: vendors can ship/override settings via a file;
  unknown keys are ignored for forward compatibility (same rule as the
  payload models).

Example::

    from py_rizmi import RizmiConfig

    config = RizmiConfig(trial_days=14, watchdog_interval_seconds=600)
    watchdog = LicenseWatchdog.from_config(config, validator, "license.lic")
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Dict

ALLOWED_KEY_SIZES = (2048, 3072, 4096)
ALLOWED_MODES = ("offline", "online")
ALLOWED_ALGORITHMS = ("RS256",)  # only supported signing algorithm


def _require_positive(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer, got {type(value).__name__}")
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def _require_non_negative(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}")


@dataclass(frozen=True)
class RizmiConfig:
    """Centralized, validated settings for all py-rizmi components.

    Every field defaults to the library's historical default, so
    ``RizmiConfig()`` behaves exactly like the unconfigured API.
    """

    # ── trial ─────────────────────────────────────────────────────────
    trial_days: int = 14

    # ── runtime enforcement (LicenseWatchdog) ────────────────────────
    watchdog_interval_seconds: int = 3600
    watchdog_strict_start: bool = False
    watch_trial: bool = False

    # ── validation ────────────────────────────────────────────────────
    check_hwid: bool = True
    clock_tolerance_seconds: int = 300
    grace_days: int = 14

    # ── issuance ──────────────────────────────────────────────────────
    max_clients: int = 10
    mode: str = "offline"
    key_size: int = 2048
    algorithm: str = "RS256"
    exp_days: int = 365

    # ── swap / revocation ────────────────────────────────────────────
    swap_valid_minutes: int = 60
    crl_next_update_hours: int = 24

    # ── naming ────────────────────────────────────────────────────────
    app_name: str = "py-rizmi"

    def __post_init__(self) -> None:
        _require_positive(self.trial_days, "trial_days")
        _require_positive(self.watchdog_interval_seconds, "watchdog_interval_seconds")
        _require_non_negative(self.clock_tolerance_seconds, "clock_tolerance_seconds")
        _require_non_negative(self.grace_days, "grace_days")
        _require_positive(self.max_clients, "max_clients")
        _require_positive(self.exp_days, "exp_days")
        _require_positive(self.swap_valid_minutes, "swap_valid_minutes")
        _require_positive(self.crl_next_update_hours, "crl_next_update_hours")

        if self.mode not in ALLOWED_MODES:
            raise ValueError(f"mode must be one of {ALLOWED_MODES}, got {self.mode!r}")
        if self.key_size not in ALLOWED_KEY_SIZES:
            raise ValueError(
                f"key_size must be one of {ALLOWED_KEY_SIZES}, got {self.key_size}"
            )
        if self.algorithm not in ALLOWED_ALGORITHMS:
            raise ValueError(
                f"algorithm must be one of {ALLOWED_ALGORITHMS}, got {self.algorithm!r}"
            )
        if not self.app_name or not isinstance(self.app_name, str):
            raise ValueError("app_name must be a non-empty string")

    # ── convenience helpers ───────────────────────────────────────────

    @classmethod
    def with_watchdog_interval(
        cls, *, minutes: int | None = None, hours: int | None = None, **kwargs: Any
    ) -> "RizmiConfig":
        """Build a config expressing the watchdog interval naturally.

        Example::

            RizmiConfig.with_watchdog_interval(minutes=1)   # 60 s
            RizmiConfig.with_watchdog_interval(hours=2)     # 7200 s
        """
        if (minutes is None) == (hours is None):
            raise ValueError("pass exactly one of minutes= or hours=")
        if minutes is not None:
            seconds = int(minutes) * 60
        else:
            assert hours is not None
            seconds = int(hours) * 3600
        return cls(watchdog_interval_seconds=seconds, **kwargs)

    # ── persistence ───────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, path: str | Path | None = None, indent: int = 2) -> str:
        """Serialize to JSON; optionally write to *path*."""
        text = json.dumps(self.to_dict(), indent=indent)
        if path is not None:
            Path(path).write_text(text)
        return text

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RizmiConfig":
        """Build from a dict; unknown keys are ignored (forward compat)."""
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    @classmethod
    def from_json(cls, path: str | Path) -> "RizmiConfig":
        """Load from a JSON file written by :meth:`to_json`."""
        text = Path(path).read_text()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid config JSON in {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"config root in {path} must be a JSON object")
        return cls.from_dict(data)

    def replace(self, **changes: Any) -> "RizmiConfig":
        """Return a new validated config with *changes* applied."""
        from dataclasses import replace as dc_replace

        return dc_replace(self, **changes)
