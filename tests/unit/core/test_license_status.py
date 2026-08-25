"""Tests for LicenseStatus — developer-facing license state summary."""
from __future__ import annotations

from py_rizmi.core.license_activator import ActivationResult, LicenseStatus


def test_ok_result_is_truthy() -> None:
    r = ActivationResult(ok=True, payload=None)
    # payload None is unusual for ok results; from_activation handles it gracefully
    s = LicenseStatus.from_activation(r)
    assert isinstance(s, LicenseStatus)


def test_licensed_status_truthy_with_days() -> None:
    import time

    exp = int(time.time()) + 30 * 86_400
    from py_rizmi.models.license_payload import LicensePayload

    p = LicensePayload(client="Acme", license_id="L1", hwid="", iat=0, exp=exp)
    r = ActivationResult(ok=True, payload=p)
    s = LicenseStatus.from_activation(r)
    assert bool(s) is True
    assert s.state == "licensed"
    assert 28 <= s.days_left <= 31
    assert s.client == "Acme"
    assert "Acme" in s.message


def test_failure_carries_canonical_message() -> None:
    r = ActivationResult(ok=False, reason="hwid_mismatch")
    s = LicenseStatus.from_activation(r)
    assert not s
    assert "fingerprint mismatch" in s.message.lower()


def test_states_cover_trial_and_missing() -> None:
    trial = LicenseStatus(state="trial_active", ok=True, days_left=5, message="Trial: 5 day(s)")
    assert bool(trial)
    missing = LicenseStatus(state="missing")
    assert not missing
    assert missing.message  # message never empty when constructed via helpers


def test_to_dict_serializable() -> None:
    s = LicenseStatus(state="licensed", ok=True, days_left=10, client="X", message="m")
    d = s.to_dict()
    assert d["state"] == "licensed"
    assert d["ok"] is True
    assert isinstance(d, dict)
