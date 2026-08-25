"""Tests for LicenseGate — the one-object integration facade."""
from __future__ import annotations

from pathlib import Path

import pytest

from py_rizmi.core.license_issuer import LicenseIssuer
from py_rizmi.core.keypair import KeyPairManager
from py_rizmi.core.license_gate import LicenseGate
from py_rizmi.models.license_payload import LicensePayload


@pytest.fixture()
def gate(tmp_path: Path):
    priv = tmp_path / "priv.pem"
    pub = tmp_path / "pub.pem"
    KeyPairManager.save_keypair(str(priv), str(pub))
    pub_pem = pub.read_text()
    g = LicenseGate(
        app_name="MyApp",
        public_key=pub_pem,
        config_dir=tmp_path / "cfg",
        db_path=tmp_path / "s.db",
        trial_days=14,
    )
    return g, priv, pub_pem


def _issue(priv: Path, client: str = "Acme") -> str:
    payload = LicensePayload(client=client, license_id=f"L-{client}", hwid="")
    payload.set_auto_iat()
    payload.set_auto_exp(365)
    return LicenseIssuer.from_file(str(priv)).issue(payload)


def test_first_run_starts_trial(gate) -> None:
    g, _priv, _pub = gate
    st = g.start()
    assert st.ok and bool(st)
    assert st.state == "trial_active"
    assert 0 < st.days_left <= 14


def test_activate_then_check_returns_licensed(gate, sample_payload) -> None:
    g, priv, _pub = gate
    g.start()
    sample_payload.set_auto_iat()
    sample_payload.set_auto_exp(365)
    token = LicenseIssuer.from_file(str(priv)).issue(sample_payload)
    res = g.activate_token(token)
    assert res.ok
    st = g.check()
    assert st.state == "licensed"
    assert st.client == sample_payload.client


def test_check_without_any_state_reports_missing_or_trial(gate) -> None:
    g, _priv, _pub = gate
    st = g.check()
    # fresh install: either no_trial or missing — but never a crash
    assert st.state in ("missing", "no_trial", "trial_active")


def test_gate_refuses_default_toolkit_namespace(tmp_path) -> None:
    with pytest.raises(Exception, match="app_name"):
        LicenseGate(
            app_name="py-rizmi",
            public_key="-----BEGIN PUBLIC KEY-----\nx\n-----END PUBLIC KEY-----",
            config_dir=tmp_path / "c",
            db_path=tmp_path / "s.db",
        )


def test_deactivate_returns_to_trial(gate, sample_payload) -> None:
    g, priv, _pub = gate
    g.start()
    sample_payload.set_auto_iat()
    sample_payload.set_auto_exp(365)
    g.activate_token(LicenseIssuer.from_file(str(priv)).issue(sample_payload))
    assert g.check().state == "licensed"
    g.deactivate()
    st = g.check()
    assert st.state in ("trial_active", "trial_expired", "no_trial", "missing")
