import pytest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from py_rizmi.gui.views.keymanager_view import KeyManagerTab


def test_keymanager_generate_keypair(qtbot: QtBot) -> None:
    """Test generating a keypair populates text areas."""
    view = KeyManagerTab()
    qtbot.addWidget(view)
    
    with patch("py_rizmi.core.keypair.KeyPairManager.generate_keypair", return_value=("private_pem_data", "public_pem_data")):
        view.btn_gen_mode.setChecked(True)
        view._on_generate()
        
    assert "private_pem_data" in view.txt_priv.toPlainText()
    assert "public_pem_data" in view.txt_pub.toPlainText()
    assert "ready" in view.lbl_gen_info.text().lower()


def test_keymanager_paste_holds_in_memory(qtbot: QtBot) -> None:
    """Test pasting keys holds them in memory and not on disk."""
    view = KeyManagerTab()
    qtbot.addWidget(view)
    
    view.btn_load_mode.setChecked(True)
    
    cb = QApplication.clipboard()
    assert cb is not None
    cb.setText("-----BEGIN PRIVATE KEY-----\ndummy_pasted_priv_key\n-----END PRIVATE KEY-----")
    view._paste_priv()
    
    assert "dummy_pasted_priv_key" in view._pasted_pem["priv"]
    assert "memory" in view.priv_entry.text()
    
    cb.setText("-----BEGIN PUBLIC KEY-----\ndummy_pasted_pub_key\n-----END PUBLIC KEY-----")
    view._paste_pub()
    
    assert "dummy_pasted_pub_key" in view._pasted_pem["pub"]
    assert "memory" in view.pub_entry.text()


def test_keymanager_validate_mismatch(qtbot: QtBot) -> None:
    """Test validate reports mismatch for unrelated keys."""
    view = KeyManagerTab()
    qtbot.addWidget(view)
    
    view.btn_load_mode.setChecked(True)
    
    # Setup mismatched keys
    view._pasted_pem["priv"] = "priv_key_data"
    view._pasted_pem["pub"] = "pub_key_data"
    view.priv_entry.setText("memory")
    view.pub_entry.setText("memory")
    view._active_source = "load"
    
    with patch("py_rizmi.core.keypair.KeyPairManager.validate_private_key", return_value=True):
        with patch("py_rizmi.core.keypair.KeyPairManager.validate_public_key", return_value=True):
            with patch("py_rizmi.core.keypair.KeyPairManager.verify_keypair", return_value=False):
                view._on_validate()
                
    assert "NOT match" in view.lbl_val_res.text()
