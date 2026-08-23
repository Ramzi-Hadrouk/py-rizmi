"""Unit tests for core.crypto.save_pem permission handling (Phase 3)."""
import os
import stat
import sys

import pytest

from py_rizmi.core.crypto import save_pem

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX permission bits not applicable on Windows"
)


def test_save_pem_creates_file_owner_only(tmp_path):
    target = tmp_path / "sub" / "key.pem"
    save_pem("-----BEGIN TEST-----\n", str(target))
    assert target.exists()
    mode = stat.S_IMODE(os.stat(target).st_mode)
    assert mode == 0o600


def test_save_pem_tightens_pre_existing_loose_file(tmp_path):
    target = tmp_path / "key.pem"
    target.write_text("old")
    os.chmod(target, 0o644)
    save_pem("-----BEGIN TEST-----\n", str(target))
    mode = stat.S_IMODE(os.stat(target).st_mode)
    assert mode == 0o600


def test_save_pem_content_written(tmp_path):
    target = tmp_path / "key.pem"
    pem = "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n"
    save_pem(pem, str(target))
    assert target.read_text() == pem


def test_keypair_manager_private_key_is_owner_only(tmp_path):
    from py_rizmi.core.keypair import KeyPairManager

    priv = tmp_path / "priv.pem"
    pub = tmp_path / "pub.pem"
    KeyPairManager.save_keypair(str(priv), str(pub))
    assert stat.S_IMODE(os.stat(priv).st_mode) == 0o600
