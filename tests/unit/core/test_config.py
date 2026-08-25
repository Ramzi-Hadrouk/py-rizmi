"""Tests for core.config.RizmiConfig — centralized validated settings."""
from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from py_rizmi.core.config import RizmiConfig


class TestDefaults:
    def test_defaults_match_historical_behavior(self):
        c = RizmiConfig()
        assert c.trial_days == 14
        assert c.watchdog_interval_seconds == 3600
        assert c.watchdog_strict_start is False
        assert c.watch_trial is False
        assert c.check_hwid is True
        assert c.clock_tolerance_seconds == 300
        assert c.grace_days == 14
        assert c.max_clients == 10
        assert c.mode == "offline"
        assert c.key_size == 2048
        assert c.algorithm == "RS256"
        assert c.exp_days == 365
        assert c.crl_next_update_hours == 24
        assert c.app_name == "py-rizmi"


class TestValidation:
    @pytest.mark.parametrize(
        "field", ["trial_days", "watchdog_interval_seconds", "max_clients",
                  "exp_days", "crl_next_update_hours"]
    )
    def test_positive_fields_reject_zero_and_negative(self, field):
        with pytest.raises(ValueError, match=field):
            RizmiConfig(**{field: 0})
        with pytest.raises(ValueError, match=field):
            RizmiConfig(**{field: -1})

    @pytest.mark.parametrize("field", ["clock_tolerance_seconds", "grace_days"])
    def test_non_negative_fields_reject_negative_only(self, field):
        RizmiConfig(**{field: 0})  # zero allowed
        with pytest.raises(ValueError, match=field):
            RizmiConfig(**{field: -5})

    @pytest.mark.parametrize(
        "field", ["trial_days", "watchdog_interval_seconds", "grace_days"]
    )
    def test_bool_rejected_for_int_fields(self, field):
        with pytest.raises(ValueError, match=field):
            RizmiConfig(**{field: True})

    def test_invalid_mode_rejected(self):
        with pytest.raises(ValueError, match="mode"):
            RizmiConfig(mode="hybrid")

    @pytest.mark.parametrize("bad", [1024, 8192, 0, -2048])
    def test_invalid_key_size_rejected(self, bad):
        with pytest.raises(ValueError, match="key_size"):
            RizmiConfig(key_size=bad)

    @pytest.mark.parametrize("allowed", [2048, 3072, 4096])
    def test_valid_key_sizes_accepted(self, allowed):
        assert RizmiConfig(key_size=allowed).key_size == allowed

    def test_invalid_algorithm_rejected(self):
        with pytest.raises(ValueError, match="algorithm"):
            RizmiConfig(algorithm="HS256")

    def test_empty_app_name_rejected(self):
        with pytest.raises(ValueError, match="app_name"):
            RizmiConfig(app_name="")

    def test_error_message_names_the_field(self):
        with pytest.raises(ValueError) as exc_info:
            RizmiConfig(trial_days=-3)
        assert "trial_days" in str(exc_info.value)


class TestImmutability:
    def test_frozen_dataclass_rejects_mutation(self):
        c = RizmiConfig()
        with pytest.raises(FrozenInstanceError):
            c.trial_days = 99  # type: ignore[misc]

    def test_replace_returns_new_instance(self):
        c = RizmiConfig(trial_days=14)
        c2 = c.replace(trial_days=30)
        assert c2.trial_days == 30
        assert c.trial_days == 14  # original untouched


class TestWatchdogIntervalHelper:
    def test_minutes(self):
        assert RizmiConfig.with_watchdog_interval(minutes=1).watchdog_interval_seconds == 60
        assert RizmiConfig.with_watchdog_interval(minutes=90).watchdog_interval_seconds == 5400

    def test_hours(self):
        assert RizmiConfig.with_watchdog_interval(hours=1).watchdog_interval_seconds == 3600
        assert RizmiConfig.with_watchdog_interval(hours=2).watchdog_interval_seconds == 7200

    def test_exactly_one_unit_required(self):
        with pytest.raises(ValueError, match="exactly one"):
            RizmiConfig.with_watchdog_interval(minutes=5, hours=2)
        with pytest.raises(ValueError, match="exactly one"):
            RizmiConfig.with_watchdog_interval()

    def test_other_kwargs_pass_through(self):
        c = RizmiConfig.with_watchdog_interval(minutes=1, trial_days=7)
        assert c.watchdog_interval_seconds == 60
        assert c.trial_days == 7


class TestJsonPersistence:
    def test_roundtrip_via_dict(self):
        c = RizmiConfig(trial_days=30, watchdog_interval_seconds=60)
        restored = RizmiConfig.from_dict(c.to_dict())
        assert restored == c

    def test_unknown_keys_ignored(self):
        c = RizmiConfig.from_dict({"trial_days": 7, "future_setting": {"x": 1}})
        assert c.trial_days == 7

    def test_json_file_roundtrip(self, tmp_path):
        path = tmp_path / "rizmi.json"
        original = RizmiConfig(watchdog_interval_seconds=120, app_name="MyApp")
        original.to_json(path)

        loaded = RizmiConfig.from_json(path)
        assert loaded == original

        # The file itself is valid JSON with the expected content.
        data = json.loads(path.read_text())
        assert data["app_name"] == "MyApp"

    def test_from_json_invalid_json_raises_valueerror(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not json")
        with pytest.raises(ValueError, match="invalid config JSON"):
            RizmiConfig.from_json(bad)

    def test_from_json_non_object_root_raises(self, tmp_path):
        bad = tmp_path / "arr.json"
        bad.write_text("[1, 2]")
        with pytest.raises(ValueError, match="JSON object"):
            RizmiConfig.from_json(bad)

    def test_loaded_config_still_validated(self, tmp_path):
        """A hand-edited config file cannot smuggle invalid values."""
        path = tmp_path / "evil.json"
        path.write_text(json.dumps({"trial_days": -10}))
        with pytest.raises(ValueError, match="trial_days"):
            RizmiConfig.from_json(path)


class TestToDict:
    def test_to_dict_covers_all_fields(self):
        import dataclasses

        c = RizmiConfig()
        d = c.to_dict()
        for f in dataclasses.fields(RizmiConfig):
            assert f.name in d
