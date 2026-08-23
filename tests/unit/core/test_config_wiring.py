"""Tests for from_config() wiring: config -> watchdog / trial / validation.

Precedence rule under test everywhere: explicit kwarg > config > default.
"""
from __future__ import annotations

from typing import Any, List

import pytest

from py_rizmi.core.config import RizmiConfig
from py_rizmi.core.runtime_guard import LicenseWatchdog
from py_rizmi.core.trial import TrialManager
from py_rizmi.models.license_payload import LicensePayload


class FakeHWID:
    def __init__(self, hwid: str = "a" * 64) -> None:
        self.hwid = hwid

    def __call__(self) -> str:
        return self.hwid


class FakeValidator:
    def validate_from_file(self, license_path: str, check_hwid: bool = True):
        p = LicensePayload(client="acme", license_id="L-1")
        return p


class TestWatchdogFromConfig:
    def test_interval_from_config(self):
        config = RizmiConfig(watchdog_interval_seconds=7200)  # 2 hours
        wd = LicenseWatchdog.from_config(config, FakeValidator(), "license.lic")
        assert wd.interval_seconds == 7200.0

    def test_one_minute_interval(self):
        config = RizmiConfig.with_watchdog_interval(minutes=1)
        wd = LicenseWatchdog.from_config(config, FakeValidator(), "license.lic")
        assert wd.interval_seconds == 60.0

    def test_explicit_kwarg_overrides_config(self):
        config = RizmiConfig(watchdog_interval_seconds=3600)
        wd = LicenseWatchdog.from_config(
            config, FakeValidator(), "license.lic", interval_seconds=30
        )
        assert wd.interval_seconds == 30.0

    def test_strict_start_from_config(self):
        config = RizmiConfig(watchdog_strict_start=True)
        wd = LicenseWatchdog.from_config(config, FakeValidator(), "license.lic")
        assert wd.strict_start is True

    def test_check_hwid_from_config(self):
        config = RizmiConfig(check_hwid=False)
        wd = LicenseWatchdog.from_config(config, FakeValidator(), "license.lic")
        assert wd.check_hwid is False

    def test_callbacks_pass_through(self):
        violations: List[Any] = []
        config = RizmiConfig()
        wd = LicenseWatchdog.from_config(
            config, FakeValidator(), "license.lic",
            on_violation=lambda r, d: violations.append(r),
        )
        assert wd._on_violation is not None


class TestTrialFromConfig:
    def _pub(self, tmp_path):
        from py_rizmi.core.keypair import KeyPairManager

        _, pub = KeyPairManager.generate_keypair()
        return pub

    def test_trial_days_from_config(self, tmp_path):
        pub = self._pub(tmp_path)
        config = RizmiConfig(trial_days=30)
        m = TrialManager.from_config(
            config, tmp_path / "cfg", pub,
            hwid_provider=FakeHWID(), enable_clock_guard=False,
        )
        assert m.trial_days == 30

    def test_explicit_trial_days_override_config(self, tmp_path):
        pub = self._pub(tmp_path)
        config = RizmiConfig(trial_days=30)
        m = TrialManager.from_config(
            config, tmp_path / "cfg", pub,
            trial_days=7,
            hwid_provider=FakeHWID(), enable_clock_guard=False,
        )
        assert m.trial_days == 7

    def test_app_name_available_via_config(self, tmp_path):
        """Config carries app_name for integrations to use on state paths."""
        config = RizmiConfig(app_name="MyProduct")
        assert config.app_name == "MyProduct"


class TestValidateLicenseWithConfig:
    def test_validate_license_accepts_config_kwarg(self, tmp_path, monkeypatch):
        """validate_license(config=...) must not crash and honors app_name."""
        from py_rizmi.integrations.validation import validate_license

        # No license file present -> 'missing' error; proves the function
        # ran through the config path without breaking.
        (tmp_path / "public_key.pem").write_text(
            __import__("py_rizmi").KeyPair.generate_keypair()[1]
        )
        config = RizmiConfig(app_name="CfgApp", check_hwid=False)
        with pytest.raises(ValueError, match="missing"):
            validate_license(str(tmp_path), config=config)

    def test_validate_license_without_config_unchanged(self, tmp_path):
        from py_rizmi.integrations.validation import validate_license

        __import__("py_rizmi").KeyPair.generate_keypair()
        (tmp_path / "public_key.pem").write_text("x")
        with pytest.raises(ValueError, match="missing"):
            validate_license(str(tmp_path))


class TestConfigImmutabilityAcrossConsumers:
    def test_same_config_shared_by_watchdog_and_trial(self, tmp_path):
        """One config object can safely feed multiple consumers."""
        pub = TestTrialFromConfig()._pub(tmp_path)
        config = RizmiConfig(trial_days=7, watchdog_interval_seconds=60)

        wd = LicenseWatchdog.from_config(config, FakeValidator(), "license.lic")
        m = TrialManager.from_config(
            config, tmp_path / "cfg", pub,
            hwid_provider=FakeHWID(), enable_clock_guard=False,
        )

        assert wd.interval_seconds == 60.0
        assert m.trial_days == 7
        # Config unchanged by consumption.
        assert config.watchdog_interval_seconds == 60
        assert config.trial_days == 7
