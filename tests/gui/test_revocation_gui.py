"""GUI tests for the License Revocation tab."""
import json

import pytest

from py_rizmi.core.keypair import KeyPairManager
from py_rizmi.core.revocation import verify_revocation_list
from py_rizmi.gui.views.revocation_view import RevocationTab


@pytest.fixture
def keypair(tmp_path):
    priv = tmp_path / "priv.pem"
    pub = tmp_path / "pub.pem"
    KeyPairManager.save_keypair(str(priv), str(pub))
    return priv, pub


def test_revoke_tab_signs_list(qtbot, keypair):
    priv, pub = keypair
    tab = RevocationTab()
    qtbot.addWidget(tab)

    tab.id_list.add_row("L-001")
    tab.id_list.add_row("L-002")
    tab.txt_key_path.setText(str(priv))
    tab._on_publish()

    output_text = tab.txt_output.toPlainText()
    assert output_text != ""
    envelope = json.loads(output_text)
    assert "payload" in envelope and "signature" in envelope
    assert tab.lbl_status.text() == "Signed successfully!"

    ok, reason, crl = verify_revocation_list(envelope, pub.read_text())
    assert ok is True and reason == "valid"
    assert crl is not None
    assert crl.revoked_ids == ["L-001", "L-002"]


def test_revoke_tab_missing_key_shows_warning(qtbot, monkeypatch):
    tab = RevocationTab()
    qtbot.addWidget(tab)
    tab.id_list.add_row("L-001")

    warned = []
    monkeypatch.setattr(
        "py_rizmi.gui.views.revocation_view.QMessageBox.warning",
        lambda *a, **k: warned.append(a),
    )
    tab._on_publish()  # no key path set
    assert warned, "expected a warning dialog for missing private key"
    assert tab.txt_output.toPlainText() == ""


def test_revoke_tab_invalid_next_update_rejected(qtbot, keypair, monkeypatch):
    priv, _ = keypair
    tab = RevocationTab()
    qtbot.addWidget(tab)
    tab.id_list.add_row("L-001")
    tab.txt_key_path.setText(str(priv))
    tab.txt_next_update.setText("not-a-number")

    warned = []
    monkeypatch.setattr(
        "py_rizmi.gui.views.revocation_view.QMessageBox.warning",
        lambda *a, **k: warned.append(a),
    )
    tab._on_publish()
    assert warned
    assert tab.txt_output.toPlainText() == ""


def test_revoke_tab_blank_ids_are_dropped(qtbot, keypair):
    priv, pub = keypair
    tab = RevocationTab()
    qtbot.addWidget(tab)
    tab.id_list.add_row("  L-KEEP  ")
    tab.txt_key_path.setText(str(priv))
    tab._on_publish()

    envelope = json.loads(tab.txt_output.toPlainText())
    _, _, crl = verify_revocation_list(envelope, pub.read_text())
    assert crl is not None and crl.revoked_ids == ["L-KEEP"]
