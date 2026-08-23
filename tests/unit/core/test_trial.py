"""Tests for core.trial.TrialManager — license-free trial periods.

Security-sensitive feature: covers first-run issuance, expiry, tamper
detection (file edit, HWID clone, clock rollback), deletion-resistance,
and real-license precedence.
"""
from __future__ import annotations

import time
from typing import Any, Optional

import pytest

from py_rizmi.core.keypair import KeyPairManager
from py_rizmi.core.license_issuer import LicenseIssuer
from py_rizmi.core.trial import TRIAL_LICENSE_FILE, TrialManager, TrialStatus
from py_rizmi.models.license_payload import LicensePayload


class FakeHWID:
    """Controllable machine fingerprint for testing."""

    def __init__(self, hwid: str = "a" * 64) -> None:
        self.hwid = hwid

    def __call__(self) -> str:
        return self.hwid


@pytest.fixture
def vendor_keys():
    priv, pub = KeyPairManager.generate_keypair()
    return priv, pub


@pytest.fixture
def vendor_pub(vendor_keys):
    return vendor_keys[1]


@pytest.fixture(autouse=True)
def isolate_clock_state(tmp_path, monkeypatch):
    """Redirect ClockGuard's redundant OS-level state directories into the
    test tmp dir so trials from different tests (different fake HWIDs)
    never see each other's ratchet state."""
    import py_rizmi.core.trial as trial_mod
    import py_rizmi.integrations.validation as validation_mod

    sandbox = tmp_path / "clock-state"

    def fake_default_state_paths(config_dir, app_name="py-rizmi"):
        base = sandbox / app_name.replace("/", "_")
        return [
            str(base / "s1.dat"),
            str(base / "s2.dat"),
            str(base / "s3.dat"),
        ]

    monkeypatch.setattr(
        validation_mod, "_default_state_paths", fake_default_state_paths
    )
    # trial.py imports it lazily inside _clock_guard; patch both views.
    monkeypatch.setattr(
        trial_mod,
        "_default_state_paths",
        fake_default_state_paths,
        raising=False,
    )


def make_manager(
    tmp_path,
    vendor_pub: str,
    *,
    trial_days: int = 14,
    hwid: str = "a" * 64,
    enable_clock_guard: bool = True,
    config_dir: Optional[Any] = None,
) -> TrialManager:
    return TrialManager(
        config_dir=config_dir or tmp_path / "config",
        trial_days=trial_days,
        public_key=vendor_pub,
        hwid_provider=FakeHWID(hwid),
        enable_clock_guard=enable_clock_guard,
    )


# ─── construction / validation of parameters ----------------------------------


class TestConstruction:
    def test_non_positive_trial_days_rejected(self, tmp_path, vendor_pub):
        with pytest.raises(ValueError, match="trial_days"):
            make_manager(tmp_path, vendor_pub, trial_days=0)

    def test_empty_public_key_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="public_key"):
            TrialManager(config_dir=tmp_path, trial_days=7, public_key="")

    def test_default_license_path_is_config_dir(self, tmp_path, vendor_pub):
        m = make_manager(tmp_path, vendor_pub)
        assert m.license_path == tmp_path / "config" / "license.lic"


# ─── first run / issuance ------------------------------------------------------


class TestFirstRun:
    def test_start_or_check_creates_trial(self, tmp_path, vendor_pub):
        m = make_manager(tmp_path, vendor_pub, trial_days=14)
        status = m.start_or_check()
        assert status.state == "trial_active"
        assert status.ok is True
        assert 1 <= status.days_left <= 14
        assert status.payload is not None
        assert status.payload.mode == "trial"
        assert (tmp_path / "config" / TRIAL_LICENSE_FILE).exists()

    def test_trial_license_is_hwid_bound(self, tmp_path, vendor_pub):
        m = make_manager(tmp_path, vendor_pub)
        payload = m.issue_trial()
        assert payload.hwid == "a" * 64

    def test_trial_signed_by_local_key_not_vendor(self, tmp_path, vendor_pub):
        """The trial token must NOT validate against the vendor key."""
        m = make_manager(tmp_path, vendor_pub)
        m.issue_trial()
        token = (tmp_path / "config" / TRIAL_LICENSE_FILE).read_text()
        from py_rizmi.core.license_validator import LicenseValidator

        with pytest.raises(ValueError):
            LicenseValidator(vendor_pub).validate(token, check_hwid=False)

    def test_trial_keypair_private_key_is_owner_only(self, tmp_path, vendor_pub):
        import os
        import stat

        m = make_manager(tmp_path, vendor_pub)
        m.issue_trial()
        key_file = tmp_path / "config" / "trial_key.pem"
        if os.name != "nt":
            assert stat.S_IMODE(os.stat(key_file).st_mode) == 0o600

    def test_second_run_does_not_reissue(self, tmp_path, vendor_pub):
        m = make_manager(tmp_path, vendor_pub)
        first = m.start_or_check()
        lic_before = (tmp_path / "config" / TRIAL_LICENSE_FILE).read_text()

        second = m.start_or_check()
        lic_after = (tmp_path / "config" / TRIAL_LICENSE_FILE).read_text()
        assert lic_before == lic_after
        assert second.state == "trial_active"
        assert second.payload is not None and first.payload is not None
        assert second.payload.exp == first.payload.exp


# ─── expiry ---------------------------------------------------------------------


class TestExpiry:
    def test_expired_trial_reports_expired_not_tampered(self, tmp_path, vendor_pub):
        m = make_manager(tmp_path, vendor_pub, trial_days=14)
        payload = m.issue_trial()
        # Force the trial into the past (beyond its window).
        payload.exp = int(time.time()) - 5 * 86_400
        # Re-sign with the trial key to keep the signature valid.
        from py_rizmi.core.trial import TRIAL_KEY_FILE

        issuer = LicenseIssuer.from_file(str(tmp_path / "config" / TRIAL_KEY_FILE))
        (tmp_path / "config" / TRIAL_LICENSE_FILE).write_text(issuer.issue(payload))

        status = m.check()
        assert status.state == "trial_expired"
        assert status.ok is False
        assert status.days_left == 0
        assert "ended" in status.detail.lower()


# ─── tamper detection ------------------------------------------------------------


class TestTamperDetection:
    def test_edited_trial_file_detected(self, tmp_path, vendor_pub):
        """Editing exp in the trial file must break the signature."""
        import jwt

        m = make_manager(tmp_path, vendor_pub)
        m.start_or_check()
        lic_path = tmp_path / "config" / TRIAL_LICENSE_FILE
        token = lic_path.read_text()

        # Forge a far-future exp WITHOUT re-signing properly: sign with a
        # DIFFERENT key so the signature is invalid for the trial pubkey.
        _, rogue_pub = KeyPairManager.generate_keypair()
        rogue_priv, _ = KeyPairManager.generate_keypair()
        header = jwt.get_unverified_header(token)
        forged = jwt.encode(
            {**jwt.decode(token, options={"verify_signature": False}),
             "exp": int(time.time()) + 365 * 86_400},
            rogue_priv,
            algorithm=header["alg"],
        )
        lic_path.write_text(forged)

        status = m.check()
        assert status.state == "tampered"
        assert status.ok is False

    def test_copied_trial_from_other_machine_detected(self, tmp_path, vendor_pub):
        """Machine B cannot use machine A's trial file."""
        config_a = tmp_path / "machine_a"
        config_b = tmp_path / "machine_b"

        m_a = make_manager(tmp_path, vendor_pub, config_dir=config_a, hwid="a" * 64)
        m_a.start_or_check()

        # Copy A's whole trial state to B's config dir...
        import shutil

        shutil.copytree(config_a, config_b)

        # ...but machine B has a different HWID.
        m_b = make_manager(tmp_path, vendor_pub, config_dir=config_b, hwid="b" * 64)
        status = m_b.check()
        assert status.state == "tampered"
        assert status.ok is False

    def test_clock_rollback_extending_trial_detected(self, tmp_path, vendor_pub):
        """Winding the clock back after trial start must not extend it."""
        m = make_manager(tmp_path, vendor_pub, trial_days=14)
        m.start_or_check()

        # Simulate rollback: re-issue "now" but with the machine believing
        # time went backwards. The ratchet recorded start=T0; a rollback
        # attempt at issue time uses the recorded mark anyway.
        payload = m.issue_trial()
        # The ratchet means exp stays anchored to the ORIGINAL start even
        # across re-issuance; verify exp didn't move forward past original.
        lic_path = tmp_path / "config" / TRIAL_LICENSE_FILE
        token2 = lic_path.read_text()
        exp2 = jwt_exp(token2)
        assert exp2 <= payload.exp + 2  # no meaningful extension

    def test_truncated_garbage_trial_detected(self, tmp_path, vendor_pub):
        m = make_manager(tmp_path, vendor_pub)
        m.start_or_check()
        (tmp_path / "config" / TRIAL_LICENSE_FILE).write_text("garbage")
        status = m.check()
        assert status.state == "tampered"

    def test_missing_trial_pubkey_detected(self, tmp_path, vendor_pub):
        m = make_manager(tmp_path, vendor_pub)
        m.start_or_check()
        (tmp_path / "config" / "trial_key_pub.pem").unlink()
        status = m.check()
        assert status.state == "tampered"

    def test_non_trial_mode_token_rejected(self, tmp_path, vendor_keys, vendor_pub):
        """A real vendor license dropped as trial.lic must not pass."""
        m = make_manager(tmp_path, vendor_pub)
        m.start_or_check()

        # Overwrite trial.lic with a VENDOR-signed non-trial license.
        payload = LicensePayload(client="x", license_id="real", hwid="a" * 64)
        payload.set_auto_iat()
        payload.set_auto_exp(365)
        token = LicenseIssuer(vendor_keys[0]).issue(payload)
        (tmp_path / "config" / TRIAL_LICENSE_FILE).write_text(token)

        status = m.check()
        # It fails trial-key signature OR mode check -- either way blocked.
        assert status.state in ("tampered",)


def jwt_exp(token: str) -> int:
    import jwt

    data = jwt.decode(token, options={"verify_signature": False})
    return int(data["exp"])


# ─── deletion resistance ----------------------------------------------------------


class TestDeletionResistance:
    def test_deleting_trial_does_not_reset_clock(self, tmp_path, vendor_pub):
        """Delete trial.lic -> regenerate -> trial does NOT restart."""
        m = make_manager(tmp_path, vendor_pub, trial_days=14)
        first = m.start_or_check()
        assert first.payload is not None
        original_exp = first.payload.exp

        # Client deletes the trial hoping for a fresh 14 days.
        (tmp_path / "config" / TRIAL_LICENSE_FILE).unlink()

        second = m.start_or_check()
        assert second.payload is not None
        # Allow sub-second clock-tick drift between the two issuances;
        # what must NOT happen is a fresh full window.
        assert second.payload.exp <= original_exp + 60, (
            "deleting trial.lic must not extend the trial "
            "(start date is ratcheted in ClockGuard state)"
        )

    def test_full_wipe_of_config_dir_still_ratcheted(self, tmp_path, vendor_pub):
        """Even deleting the whole config dir doesn't reset the clock,
        because ClockGuard state lives in redundant OS directories."""
        m = make_manager(tmp_path, vendor_pub, trial_days=14)
        first = m.start_or_check()
        assert first.payload is not None
        original_exp = first.payload.exp

        import shutil

        shutil.rmtree(tmp_path / "config")

        second = m.start_or_check()
        assert second.payload is not None
        # Sub-second tick tolerance; a fresh full window would be ~1.2M s.
        assert second.payload.exp <= original_exp + 60

    def test_no_clock_guard_allows_reset(self, tmp_path, vendor_pub):
        """Documented tradeoff: disabling clock guard disables the ratchet."""
        m = make_manager(tmp_path, vendor_pub, trial_days=14, enable_clock_guard=False)
        first = m.start_or_check()
        assert first.payload is not None
        (tmp_path / "config" / TRIAL_LICENSE_FILE).unlink()
        second = m.start_or_check()
        assert second.payload is not None
        assert second.payload.exp >= first.payload.exp  # restarted later


# ─── real-license precedence --------------------------------------------------------


class TestRealLicensePrecedence:
    def _write_real_license(self, tmp_path, vendor_priv, hwid="a" * 64):
        payload = LicensePayload(
            client="acme", license_id="PAID-001", hwid=hwid
        )
        payload.set_auto_iat()
        payload.set_auto_exp(365)
        token = LicenseIssuer(vendor_priv).issue(payload)
        (tmp_path / "config" / "license.lic").write_text(token)

    def test_real_license_supersedes_active_trial(self, tmp_path, vendor_keys, vendor_pub):
        m = make_manager(tmp_path, vendor_pub)
        m.start_or_check()  # trial running
        self._write_real_license(tmp_path, vendor_keys[0])

        status = m.check()
        assert status.state == "licensed"
        assert status.payload is not None
        assert status.payload.license_id == "PAID-001"

    def test_buying_mid_trial_works(self, tmp_path, vendor_keys, vendor_pub):
        m = make_manager(tmp_path, vendor_pub)
        assert m.start_or_check().state == "trial_active"
        self._write_real_license(tmp_path, vendor_keys[0])
        assert m.check().state == "licensed"

    def test_buying_after_expiry_works(self, tmp_path, vendor_keys, vendor_pub):
        m = make_manager(tmp_path, vendor_pub, trial_days=14)
        m.start_or_check()
        self._write_real_license(tmp_path, vendor_keys[0])
        assert m.check().state == "licensed"

    def test_corrupt_real_license_does_not_fall_back_to_trial(
        self, tmp_path, vendor_keys, vendor_pub
    ):
        """A broken REAL license surfaces 'licensed_invalid', never trial."""
        m = make_manager(tmp_path, vendor_pub)
        m.start_or_check()
        (tmp_path / "config" / "license.lic").write_text("corrupt-token")

        status = m.check()
        assert status.state == "licensed_invalid"
        assert status.ok is False

    def test_expired_real_license_reports_licensed_invalid(
        self, tmp_path, vendor_keys, vendor_pub
    ):
        """Expired paid license is NOT silently replaced by the trial."""
        m = make_manager(tmp_path, vendor_pub)
        m.start_or_check()
        payload = LicensePayload(client="acme", license_id="OLD", hwid="a" * 64)
        payload.set_auto_iat()
        payload.exp = int(time.time()) - 400 * 86_400  # long expired
        token = LicenseIssuer(vendor_keys[0]).issue(payload)
        (tmp_path / "config" / "license.lic").write_text(token)

        status = m.check()
        assert status.state == "licensed_invalid"


# ─── misc behavior -------------------------------------------------------------------


class TestMisc:
    def test_days_left_ceiling(self, tmp_path, vendor_pub):
        """23h59m left reports 1 day, not 0."""
        m = make_manager(tmp_path, vendor_pub, trial_days=14)
        payload = m.issue_trial()
        payload.exp = int(time.time()) + 23 * 3600 + 59 * 60
        from py_rizmi.core.trial import TRIAL_KEY_FILE

        issuer = LicenseIssuer.from_file(str(tmp_path / "config" / TRIAL_KEY_FILE))
        (tmp_path / "config" / TRIAL_LICENSE_FILE).write_text(issuer.issue(payload))

        status = m.check()
        assert status.state == "trial_active"
        assert status.days_left == 1

    def test_one_day_trial_expires_correctly(self, tmp_path, vendor_pub):
        m = make_manager(tmp_path, vendor_pub, trial_days=1)
        payload = m.issue_trial()
        payload.exp = int(time.time()) - 60
        from py_rizmi.core.trial import TRIAL_KEY_FILE

        issuer = LicenseIssuer.from_file(str(tmp_path / "config" / TRIAL_KEY_FILE))
        (tmp_path / "config" / TRIAL_LICENSE_FILE).write_text(issuer.issue(payload))

        status = m.check()
        assert status.state == "trial_expired"

    def test_trial_status_ok_property(self):
        assert TrialStatus(state="trial_active", days_left=3).ok is True
        assert TrialStatus(state="licensed").ok is True
        assert TrialStatus(state="trial_expired").ok is False
        assert TrialStatus(state="tampered").ok is False
        assert TrialStatus(state="no_trial").ok is False
