from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QPushButton
from pytestqt.qtbot import QtBot

from py_rizmi.gui.views.keymanager_view import KeyManagerTab


def test_keymanager_generate_keypair(qtbot: QtBot) -> None:
    """Test generating a keypair populates text areas."""
    view = KeyManagerTab()
    qtbot.addWidget(view)

    with patch(
        "py_rizmi.core.keypair.KeyPairManager.generate_keypair",
        return_value=("private_pem_data", "public_pem_data"),
    ):
        view._set_mode("generate")
        view._on_generate()

    assert "private_pem_data" in view.txt_priv.toPlainText()
    assert "public_pem_data" in view.txt_pub.toPlainText()
    assert "ready" in view.lbl_gen_info.text().lower()


def test_keymanager_paste_holds_in_memory(qtbot: QtBot) -> None:
    """Test pasting keys holds them in memory and not on disk.

    The real X11 clipboard cannot be set in headless CI environments
    (QXcbClipboard::setMimeData: Cannot set X11 selection owner), so we mock
    QApplication.clipboard() to return a controlled fake instead of writing
    to the actual system clipboard.
    """
    view = KeyManagerTab()
    qtbot.addWidget(view)

    view._set_mode("load")

    priv_pem = (
        "-----BEGIN PRIVATE KEY-----\ndummy_pasted_priv_key\n-----END PRIVATE KEY-----"
    )
    pub_pem = (
        "-----BEGIN PUBLIC KEY-----\ndummy_pasted_pub_key\n-----END PUBLIC KEY-----"
    )

    mock_cb = MagicMock()
    mock_cb.text.return_value = priv_pem
    with patch(
        "py_rizmi.gui.views.keymanager_view.QApplication.clipboard",
        return_value=mock_cb,
    ):
        view._paste_priv()

    assert "dummy_pasted_priv_key" in view._pasted_pem["priv"]
    assert "memory" in view.priv_entry.text()

    mock_cb.text.return_value = pub_pem
    with patch(
        "py_rizmi.gui.views.keymanager_view.QApplication.clipboard",
        return_value=mock_cb,
    ):
        view._paste_pub()

    assert "dummy_pasted_pub_key" in view._pasted_pem["pub"]
    assert "memory" in view.pub_entry.text()


def test_keymanager_validate_mismatch(qtbot: QtBot) -> None:
    """Test validate reports mismatch for unrelated keys."""
    view = KeyManagerTab()
    qtbot.addWidget(view)

    view._set_mode("load")

    view._pasted_pem["priv"] = "priv_key_data"
    view._pasted_pem["pub"] = "pub_key_data"
    view.priv_entry.setText("memory")
    view.pub_entry.setText("memory")

    with patch(
        "py_rizmi.core.keypair.KeyPairManager.validate_private_key", return_value=True
    ):
        with patch(
            "py_rizmi.core.keypair.KeyPairManager.validate_public_key",
            return_value=True,
        ):
            with patch(
                "py_rizmi.core.keypair.KeyPairManager.verify_keypair",
                return_value=False,
            ):
                view._on_validate()

    assert "NOT match" in view.lbl_val_res.text()


def test_validate_only_on_validate_tab(qtbot: QtBot) -> None:
    """Validate UI belongs to Validate Keypair tab, not Generate."""
    view = KeyManagerTab()
    qtbot.addWidget(view)

    assert view.btn_load_mode.text() == "Validate Keypair"
    assert "Load Existing" not in view.btn_load_mode.text()

    view._set_mode("generate")
    gen_page = view.stack.widget(0)
    assert gen_page is not None
    gen_buttons = [b.text() for b in gen_page.findChildren(QPushButton)]
    assert "Validate Keypair" not in gen_buttons

    view._set_mode("load")
    load_page = view.stack.widget(1)
    assert load_page is not None
    load_buttons = [b.text() for b in load_page.findChildren(QPushButton)]
    assert "Validate Keypair" in load_buttons
    assert view.btn_validate.parentWidget() is not None


def test_generate_tab_shows_algorithm_help_text(qtbot: QtBot) -> None:
    """Test that Generate tab displays help text about RSA algorithm and passphrase."""
    from PyQt6.QtWidgets import QLabel

    view = KeyManagerTab()
    qtbot.addWidget(view)

    view._set_mode("generate")
    gen_page = view.stack.widget(0)
    assert gen_page is not None

    # Find all labels in the Generate page
    labels = [label.text() for label in gen_page.findChildren(QLabel)]
    help_texts = [text for text in labels if "RSA algorithm" in text and "AES encryption" in text]

    assert len(help_texts) > 0, "Help text about RSA algorithm and AES encryption not found"


def test_use_for_generation_button_only_in_generate_tab(qtbot: QtBot) -> None:
    """Test that 'Use for License Generation' button only appears in Generate tab."""
    view = KeyManagerTab()
    qtbot.addWidget(view)

    # Check Generate tab has the button
    view._set_mode("generate")
    gen_page = view.stack.widget(0)
    assert gen_page is not None
    gen_buttons = [b.text() for b in gen_page.findChildren(QPushButton)]
    assert "Use for License Generation" in gen_buttons

    # Check Load/Validate tab does NOT have the button
    view._set_mode("load")
    load_page = view.stack.widget(1)
    assert load_page is not None
    load_buttons = [b.text() for b in load_page.findChildren(QPushButton)]
    assert "Use for License Generation" not in load_buttons
