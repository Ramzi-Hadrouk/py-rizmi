"""Tests for LicenseGate.status_summary() and watchdog wiring."""
from __future__ import annotations

import sqlite3
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
    violations: list[tuple[str, str]] = []
    g = LicenseGate(
        app_name="MyApp",
        public_key=pub_pem,
        config_dir=tmp_path / "cfg",
        db_path=tmp_path / "s.db",
        enable_watchdog=True,
        on_violation=lambda reason, detail: violations.append((reason, detail)),
    )
    return g, priv, pub_pem, violations


def _token(priv: Path, sample_payload) -> str:
    sample_payload.set_auto_iat()
    sample_payload.set_auto_exp(365)
    return LicenseIssuer.from_file(str(priv)).issue(sample_payload)


def test_status_summary_is_serializable(gate, sample_payload) -> None:
    g, priv, _pub, _v = gate
    g.start()
    g.activate_token(_token(priv, sample_payload))
    d = g.status_summary()
    assert isinstance(d, dict)
    assert d["state"] == "licensed"
    assert d["client"] == sample_payload.client
    assert "message" in d and isinstance(d["days_left"], int)


def test_watchdog_fires_on_tamper(gate, sample_payload, tmp_path) -> None:
    g, priv, _pub, violations = gate
    g.start()
    g.activate_token(_token(priv, sample_payload))
    # corrupt the active license row behind the watchdog's back
    with sqlite3.connect(g.store.db_path) as conn:
        conn.execute("UPDATE licenses SET token='forged' WHERE slot='active'")
        conn.commit()
    st = g.check()
    assert not st.ok
    # watchdog polls synchronously here via explicit recheck hook
    g.recheck_now()
    assert any("tampered" in r or r for r, _ in violations), violations


def test_no_watchdog_by_default(tmp_path) -> None:
    KeyPairManager.save_keypair(
        str(tmp_path / "p.pem"), str(tmp_path / "q.pem")
    )
    pub_pem = (tmp_path / "q.pem").read_text()
    g = LicenseGate(
        app_name="MyApp", public_key=pub_pem,
        config_dir=tmp_path / "cfg", db_path=tmp_path / "s.db",
    )
    assert g._watchdog is None
