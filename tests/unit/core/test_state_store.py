"""Tests for the SQLite-backed tamper-evident state store."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from py_rizmi.core.state_store import StateStore, StateStoreError


@pytest.fixture()
def store(tmp_path: Path) -> StateStore:
    return StateStore(tmp_path / "state.db", machine_id="m1", app_name="MyApp")


def test_put_get_roundtrip(store: StateStore) -> None:
    store.put("role-a", {"last_seen": 100})
    assert store.get("role-a") == {"last_seen": 100}


def test_missing_role_returns_none(store: StateStore) -> None:
    assert store.get("nope") is None


def test_tampered_payload_detected(store: StateStore, tmp_path: Path) -> None:
    store.put("role-a", {"last_seen": 100})
    conn = sqlite3.connect(tmp_path / "state.db")
    conn.execute(
        "UPDATE state SET payload = ? WHERE role = 'role-a'",
        [json.dumps({"last_seen": 9999})],
    )
    conn.commit()
    conn.close()
    assert store.get("role-a") is None
    report = store.verify()
    assert not report.ok
    assert "state:role-a" in report.tampered_roles


def test_tampered_row_hmac_detected(store: StateStore, tmp_path: Path) -> None:
    store.put("role-a", {"v": 1})
    conn = sqlite3.connect(tmp_path / "state.db")
    conn.execute("UPDATE state SET hmac = 'deadbeef' WHERE role = 'role-a'")
    conn.commit()
    conn.close()
    assert store.get("role-a") is None
    assert "state:role-a" in store.verify().tampered_roles


def test_machine_binding(store: StateStore, tmp_path: Path) -> None:
    store.put("role-a", {"v": 1})
    other = StateStore(tmp_path / "state.db", machine_id="other", app_name="MyApp")
    assert other.get("role-a") is None
    assert "state:role-a" in other.verify().tampered_roles


def test_app_namespacing_blocks_transplant(tmp_path: Path) -> None:
    a = StateStore(tmp_path / "a.db", machine_id="m1", app_name="AppA")
    a.put("role-a", {"v": 1})
    b = StateStore(tmp_path / "a.db", machine_id="m1", app_name="AppB")
    assert b.get("role-a") is None  # transplanted DB unreadable under another app


def test_schema_version_enforced(tmp_path: Path) -> None:
    db = tmp_path / "s.db"
    store = StateStore(db, machine_id="m1", app_name="MyApp")
    conn = sqlite3.connect(db)
    conn.execute("UPDATE store_meta SET value='99' WHERE key='schema_version'")
    conn.commit()
    conn.close()
    with pytest.raises(StateStoreError):
        StateStore(db, machine_id="m1", app_name="MyApp")


def test_keys_table_roundtrip(store: StateStore) -> None:
    pem = "-----BEGIN PUBLIC KEY-----\nabc\n-----END PUBLIC KEY-----"
    store.put_key("trial_public", pem)
    assert store.get_key("trial_public") == pem
    assert store.get_key("missing") is None


def test_key_tamper_detected(store: StateStore, tmp_path: Path) -> None:
    pem = "-----BEGIN PUBLIC KEY-----\nabc\n-----END PUBLIC KEY-----"
    store.put_key("trial_public", pem)
    conn = sqlite3.connect(tmp_path / "state.db")
    conn.execute("UPDATE keys SET pem='forged' WHERE role='trial_public'")
    conn.commit()
    conn.close()
    assert store.get_key("trial_public") is None


def test_concurrent_instances_interop(tmp_path: Path) -> None:
    s1 = StateStore(tmp_path / "s.db", machine_id="m1", app_name="MyApp")
    s2 = StateStore(tmp_path / "s.db", machine_id="m1", app_name="MyApp")
    s1.put("r", {"n": 1})
    assert s2.get("r") == {"n": 1}
    s2.put("r", {"n": 2})
    assert s1.get("r") == {"n": 2}


def test_delete_role(store: StateStore) -> None:
    store.put("r", {"n": 1})
    store.delete("r")
    assert store.get("r") is None


def test_license_roundtrip(store: StateStore) -> None:
    token = "eyJhbGciOiJSUzI1NiJ9.faketoken.sig"
    lic = store.put_license(token, license_id="deploy-001")
    assert lic.license_id == "deploy-001"
    active = store.active_license()
    assert active is not None and active.license_id == "deploy-001"
    assert active.token == token
    assert store.get_license("deploy-001") == token
    assert store.get_license("nope") is None


def test_active_slot_replaced_atomically(store: StateStore) -> None:
    store.put_license("token-one", license_id="L1")
    store.put_license("token-two", license_id="L2")
    active = store.active_license()
    assert active is not None and active.token == "token-two"
    # only one row flagged active
    with sqlite3.connect(store.db_path) as conn:
        rows = conn.execute(
            "SELECT slot FROM licenses WHERE slot='active'"
        ).fetchall()
    assert len(rows) == 1


def test_license_tamper_detected(store: StateStore, tmp_path: Path) -> None:
    store.put_license("good-token", license_id="L1")
    conn = sqlite3.connect(tmp_path / "state.db")
    conn.execute("UPDATE licenses SET token='forged-token' WHERE license_id='L1'")
    conn.commit()
    conn.close()
    assert store.active_license() is None
    assert "licenses:L1" in store.verify().tampered_roles


def test_default_namespace_refused(tmp_path: Path) -> None:
    with pytest.raises(StateStoreError, match="app_name"):
        StateStore(tmp_path / "s.db", machine_id="m1", app_name="py-rizmi")


def test_default_namespace_allowed_for_tests(tmp_path: Path) -> None:
    s = StateStore(
        tmp_path / "s.db",
        machine_id="m1",
        app_name="py-rizmi",
        allow_default_namespace=True,
    )
    assert s.app_name == "py-rizmi"


def test_verify_reports_ok_on_clean_store(store: StateStore) -> None:
    store.put("r", {"n": 1})
    report = store.verify()
    assert report.ok
    assert report.tampered_roles == []
