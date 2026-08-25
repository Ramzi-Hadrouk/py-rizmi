"""Tests for LicenseActivator — validated license entry into the store."""
from __future__ import annotations

from pathlib import Path

import pytest

from py_rizmi.core.license_activator import ActivationResult, LicenseActivator
from py_rizmi.core.license_issuer import LicenseIssuer
from py_rizmi.core.state_store import StateStore
from py_rizmi.models.license_payload import LicensePayload


@pytest.fixture()
def store(tmp_path: Path) -> StateStore:
    return StateStore(tmp_path / "state.db", machine_id="m1", app_name="MyApp")


def _issue(priv: Path, license_id: str = "deploy-001", hwid: str = "") -> str:
    payload = LicensePayload(
        client="Acme",
        license_id=license_id,
        hwid=hwid,
        grace_days=0,
    )
    payload.set_auto_iat()
    payload.set_auto_exp(365)
    return LicenseIssuer.from_file(str(priv)).issue(payload)


@pytest.fixture()
def keypair(tmp_path: Path):
    from py_rizmi.core.keypair import KeyPairManager

    priv = tmp_path / "private.pem"
    pub = tmp_path / "public.pem"
    KeyPairManager.save_keypair(str(priv), str(pub))
    with open(pub) as f:
        pub_pem = f.read()
    return priv, pub_pem


@pytest.fixture()
def activator(store: StateStore, keypair) -> LicenseActivator:
    _, pub_pem = keypair
    return LicenseActivator(store, pub_pem, check_hwid=False)


def test_activate_token_valid(activator: LicenseActivator, keypair) -> None:
    priv, _ = keypair
    token = _issue(priv)
    result = activator.activate_token(token)
    assert isinstance(result, ActivationResult)
    assert result.ok
    assert result.payload is not None
    assert result.payload.client == "Acme"
    # retrievable afterwards
    current = activator.current()
    assert current is not None and current.license_id == "deploy-001"


def test_activate_token_tampered_rejects_and_stores_nothing(
    activator: LicenseActivator, keypair
) -> None:
    priv, _ = keypair
    token = _issue(priv)
    header, body, sig = token.split(".")
    forged = f"{header}.{body[:-4]}AAAA.{sig}"
    result = activator.activate_token(forged)
    assert not result.ok
    assert result.reason == "tampered"
    assert activator.current() is None


def test_activate_token_expired_rejected(activator: LicenseActivator, keypair) -> None:
    priv, _ = keypair
    payload = LicensePayload(
        client="Old", license_id="old-001", hwid="", grace_days=0, iat=1_000_000, exp=2_000_000
    )
    token = LicenseIssuer.from_file(str(priv)).issue(payload)
    result = activator.activate_token(token)
    assert not result.ok
    assert result.reason == "expired"


def test_activate_hwid_mismatch_when_checked(keypair, store: StateStore) -> None:
    priv, pub_pem = keypair
    token = _issue(priv, hwid="deadbeef" * 8)
    activator = LicenseActivator(
        store, pub_pem, check_hwid=True, hwid_provider=lambda: "cafebabe" * 8
    )
    result = activator.activate_token(token)
    assert not result.ok
    assert result.reason == "hwid_mismatch"


def test_activate_file(activator: LicenseActivator, keypair, tmp_path: Path) -> None:
    priv, _ = keypair
    token = _issue(priv)
    lic = tmp_path / "license.lic"
    lic.write_text(token)
    result = activator.activate_file(lic)
    assert result.ok
    assert activator.current() is not None


def test_reactivation_swaps_active_slot(activator: LicenseActivator, keypair) -> None:
    priv, _ = keypair
    t1 = _issue(priv, license_id="L1")
    t2 = _issue(priv, license_id="L2")
    assert activator.activate_token(t1).ok
    assert activator.activate_token(t2).ok
    current = activator.current()
    assert current is not None and current.license_id == "L2"
    report = activator.store.verify()
    assert report.ok  # old row archived cleanly, nothing tampered


def test_row_tampered_after_activation_detected(
    activator: LicenseActivator, keypair, tmp_path: Path
) -> None:
    import sqlite3

    priv, _ = keypair
    token = _issue(priv)
    activator.activate_token(token)
    db = tmp_path / "state.db"
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE licenses SET token='forged' WHERE slot='active'")
        conn.commit()
    assert activator.current() is None


def test_deactivate(activator: LicenseActivator, keypair) -> None:
    priv, _ = keypair
    activator.activate_token(_issue(priv))
    activator.deactivate()
    assert activator.current() is None


def test_garbage_input_rejected(activator: LicenseActivator) -> None:
    result = activator.activate_token("not a jwt")
    assert not result.ok
    assert result.reason in ("decode_error", "tampered")
