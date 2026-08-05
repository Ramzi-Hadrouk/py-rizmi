"""Keypair Management for PyQt6."""
from __future__ import annotations

from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QFileDialog, QScrollArea, QFrame,
    QStackedWidget, QMessageBox, QApplication, QLineEdit,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication

from ...core.keypair import KeyPairManager
from ..theme import Color, button_stylesheet, input_stylesheet
from ..widgets.step_card import StepCard


class KeyManagerTab(QWidget):
    """Manage RSA keypairs — generate, load, and validate."""

    def __init__(self, app: Any = None) -> None:
        super().__init__()
        self.app = app
        self._pasted_pem: dict[str, str] = {}
        self._active_source = "generate"
        self._last_saved_priv_path: str | None = None
        self._build()

    def _build(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")

        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(12)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        title = QLabel("Key Management")
        title.setObjectName("PageTitle")
        self.content_layout.addWidget(title)
        subtitle = QLabel(
            "Generate or load an RSA keypair, validate it, then send it to License Generation."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        self.content_layout.addWidget(subtitle)

        self._build_source_card()
        self._build_validate_card()

    def _build_source_card(self) -> None:
        card = StepCard(step=1, title="Key Source")
        self.content_layout.addWidget(card)

        switcher = QFrame()
        switcher_layout = QHBoxLayout(switcher)
        switcher_layout.setContentsMargins(0, 0, 0, 14)
        switcher_layout.setSpacing(0)

        self.btn_gen_mode = QPushButton("Generate New Keypair")
        self.btn_load_mode = QPushButton("Load Existing Keys")

        style = f"""
            QPushButton {{
                background-color: {Color.PANEL_BG};
                border: 1px solid {Color.BORDER};
                padding: 8px 12px;
                font-weight: bold;
                color: {Color.FG_MUTED};
            }}
            QPushButton:checked {{
                background-color: {Color.ACCENT};
                color: {Color.WHITE};
            }}
            QPushButton:focus {{
                border: 2px solid {Color.ACCENT_HOVER};
            }}
        """
        self.btn_gen_mode.setStyleSheet(
            style + "border-top-left-radius: 6px; border-bottom-left-radius: 6px;"
        )
        self.btn_load_mode.setStyleSheet(
            style + "border-top-right-radius: 6px; border-bottom-right-radius: 6px;"
        )
        self.btn_gen_mode.setCheckable(True)
        self.btn_load_mode.setCheckable(True)
        self.btn_gen_mode.setChecked(True)
        self.btn_gen_mode.setAccessibleName("Generate new keypair mode")
        self.btn_load_mode.setAccessibleName("Load existing keys mode")

        switcher_layout.addWidget(self.btn_gen_mode)
        switcher_layout.addWidget(self.btn_load_mode)
        switcher_layout.addStretch()
        card.body_layout.addWidget(switcher)

        self.stack = QStackedWidget()
        card.body_layout.addWidget(self.stack)

        self.btn_gen_mode.clicked.connect(lambda: self._set_mode("generate"))
        self.btn_load_mode.clicked.connect(lambda: self._set_mode("load"))

        self._build_generate_panel()
        self._build_load_panel()

    def _set_mode(self, mode: str) -> None:
        self._active_source = mode
        if mode == "generate":
            self.btn_gen_mode.setChecked(True)
            self.btn_load_mode.setChecked(False)
            self.stack.setCurrentIndex(0)
        else:
            self.btn_gen_mode.setChecked(False)
            self.btn_load_mode.setChecked(True)
            self.stack.setCurrentIndex(1)

    def _build_generate_panel(self) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        ctrl = QHBoxLayout()
        lbl_size = QLabel("Key Size:")
        lbl_size.setStyleSheet(f"font-weight: bold; color: {Color.FG_MUTED};")
        ctrl.addWidget(lbl_size)

        self.combo_size = QComboBox()
        self.combo_size.addItems([str(s) for s in KeyPairManager.KEY_SIZES])
        self.combo_size.setCurrentText(str(KeyPairManager.DEFAULT_KEY_SIZE))
        self.combo_size.setAccessibleName("Key size")
        ctrl.addWidget(self.combo_size)

        lbl_pw = QLabel("Passphrase:")
        lbl_pw.setStyleSheet(f"font-weight: bold; color: {Color.FG_MUTED};")
        ctrl.addWidget(lbl_pw)

        self.gen_pw_entry = QLineEdit()
        self.gen_pw_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.gen_pw_entry.setPlaceholderText("Optional")
        self.gen_pw_entry.setStyleSheet(input_stylesheet())
        self.gen_pw_entry.setAccessibleName("Key generation passphrase")
        ctrl.addWidget(self.gen_pw_entry, stretch=1)

        btn_gen = QPushButton("Generate Keypair")
        btn_gen.setStyleSheet(button_stylesheet("primary"))
        btn_gen.setAccessibleName("Generate keypair")
        btn_gen.clicked.connect(self._on_generate)
        ctrl.addWidget(btn_gen)
        layout.addLayout(ctrl)

        self.lbl_gen_info = QLabel("")
        self.lbl_gen_info.setWordWrap(True)
        layout.addWidget(self.lbl_gen_info)

        pem_layout = QHBoxLayout()
        layout.addLayout(pem_layout)

        def _make_pem_card(
            title: str,
        ) -> tuple[QFrame, QTextEdit, QPushButton, QPushButton]:
            frm = QFrame()
            frm.setObjectName("Panel")
            lay = QVBoxLayout(frm)

            lbl_title = QLabel(title)
            lbl_title.setStyleSheet("font-weight: bold;")
            lay.addWidget(lbl_title)

            txt = QTextEdit()
            txt.setReadOnly(True)
            txt.setStyleSheet(
                f"font-family: monospace; font-size: 11px; {input_stylesheet()}"
            )
            txt.setMinimumHeight(120)
            txt.setAccessibleName(title)
            lay.addWidget(txt, stretch=1)

            btns = QHBoxLayout()
            btns.setAlignment(Qt.AlignmentFlag.AlignLeft)
            btn_save = QPushButton("Save")
            btn_copy = QPushButton("Copy")
            btn_save.setStyleSheet(button_stylesheet("secondary"))
            btn_copy.setStyleSheet(button_stylesheet("secondary"))
            btns.addWidget(btn_save)
            btns.addWidget(btn_copy)
            lay.addLayout(btns)
            return frm, txt, btn_save, btn_copy

        p_frm, self.txt_priv, p_save, p_copy = _make_pem_card("Private Key")
        p_save.setStyleSheet(button_stylesheet("warning"))
        p_save.clicked.connect(self._save_private)
        p_copy.clicked.connect(self._copy_private)
        pem_layout.addWidget(p_frm)

        u_frm, self.txt_pub, u_save, u_copy = _make_pem_card("Public Key")
        u_save.clicked.connect(self._save_public)
        u_copy.clicked.connect(self._copy_public)
        pem_layout.addWidget(u_frm)

        handoff = QHBoxLayout()
        self.btn_use_for_gen = QPushButton("Use for License Generation")
        self.btn_use_for_gen.setStyleSheet(button_stylesheet("primary"))
        self.btn_use_for_gen.setToolTip(
            "Send the current private key to the License Generation panel"
        )
        self.btn_use_for_gen.clicked.connect(self._use_for_generation)
        handoff.addWidget(self.btn_use_for_gen)
        handoff.addStretch()
        layout.addLayout(handoff)

        self.stack.addWidget(panel)

    def _build_load_panel(self) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        lbl_tip = QLabel(
            "Browse for .pem files on disk, or paste PEM content from the clipboard."
        )
        lbl_tip.setStyleSheet(f"color: {Color.FG_MUTED};")
        lbl_tip.setWordWrap(True)
        layout.addWidget(lbl_tip)

        def _make_load_row(title: str) -> tuple[QLineEdit, QPushButton, QPushButton]:
            lbl = QLabel(title)
            lbl.setStyleSheet("font-weight: bold;")
            layout.addWidget(lbl)

            row = QHBoxLayout()
            entry = QLineEdit()
            entry.setReadOnly(True)
            entry.setStyleSheet(input_stylesheet())
            entry.setAccessibleName(title)
            row.addWidget(entry)

            btn_browse = QPushButton("Browse…")
            btn_paste = QPushButton("Paste")
            btn_browse.setStyleSheet(button_stylesheet("secondary"))
            btn_paste.setStyleSheet(button_stylesheet("secondary"))
            btn_browse.setMinimumWidth(80)
            btn_paste.setMinimumWidth(70)
            row.addWidget(btn_browse)
            row.addWidget(btn_paste)
            layout.addLayout(row)
            return entry, btn_browse, btn_paste

        self.priv_entry, self.priv_btn_browse, self.priv_btn_paste = _make_load_row(
            "Private Key File:"
        )

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background-color: {Color.BORDER};")
        layout.addWidget(div)

        self.pub_entry, self.pub_btn_browse, self.pub_btn_paste = _make_load_row(
            "Public Key File:"
        )

        self.priv_btn_browse.clicked.connect(self._browse_priv)
        self.pub_btn_browse.clicked.connect(self._browse_pub)
        self.priv_btn_paste.clicked.connect(self._paste_priv)
        self.pub_btn_paste.clicked.connect(self._paste_pub)

        handoff = QHBoxLayout()
        btn_use = QPushButton("Use for License Generation")
        btn_use.setStyleSheet(button_stylesheet("primary"))
        btn_use.clicked.connect(self._use_for_generation)
        handoff.addWidget(btn_use)
        handoff.addStretch()
        layout.addLayout(handoff)

        self.stack.addWidget(panel)

    def _build_validate_card(self) -> None:
        card = StepCard(step=2, title="Validate Keypair")
        self.content_layout.addWidget(card)

        lbl_desc = QLabel(
            "Confirm that the private and public keys belong to the same RSA keypair."
        )
        lbl_desc.setStyleSheet(f"color: {Color.FG_MUTED};")
        lbl_desc.setWordWrap(True)
        card.body_layout.addWidget(lbl_desc)

        pw_row = QHBoxLayout()
        lbl_val_pw = QLabel("Private Key Passphrase:")
        lbl_val_pw.setStyleSheet(f"font-weight: bold; color: {Color.FG_MUTED};")
        self.val_pw_entry = QLineEdit()
        self.val_pw_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.val_pw_entry.setPlaceholderText(
            "Required only if private key is encrypted"
        )
        self.val_pw_entry.setStyleSheet(input_stylesheet())
        self.val_pw_entry.setAccessibleName("Validation passphrase")
        pw_row.addWidget(lbl_val_pw)
        pw_row.addWidget(self.val_pw_entry, stretch=1)
        card.body_layout.addLayout(pw_row)

        act_row = QHBoxLayout()
        act_row.setAlignment(Qt.AlignmentFlag.AlignLeft)

        btn_val = QPushButton("Validate Keypair")
        btn_val.setMinimumHeight(36)
        btn_val.setMinimumWidth(160)
        btn_val.setStyleSheet(button_stylesheet("primary"))
        btn_val.clicked.connect(self._on_validate)
        act_row.addWidget(btn_val)

        self.lbl_val_res = QLabel("")
        self.lbl_val_res.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.lbl_val_res.setWordWrap(True)
        act_row.addWidget(self.lbl_val_res, stretch=1)

        card.body_layout.addLayout(act_row)

    def _get_private_pem(self) -> str:
        return self.txt_priv.toPlainText().strip()

    def _get_public_pem(self) -> str:
        return self.txt_pub.toPlainText().strip()

    def _read_file(self, path: str) -> str:
        if not path:
            return ""
        try:
            with open(path) as f:
                return f.read().strip()
        except Exception:
            return ""

    def _get_load_priv_pem(self) -> str:
        return str(self._pasted_pem.get("priv") or self._read_file(self.priv_entry.text()))

    def _get_load_pub_pem(self) -> str:
        return str(self._pasted_pem.get("pub") or self._read_file(self.pub_entry.text()))

    def _active_private_pem(self) -> str:
        if self._active_source == "generate":
            return self._get_private_pem()
        return self._get_load_priv_pem()

    def _active_passphrase(self) -> str | None:
        if self._active_source == "generate":
            return self.gen_pw_entry.text() or None
        return self.val_pw_entry.text() or None

    def _busy(self, on: bool) -> None:
        if QGuiApplication.instance() is None:
            return
        if on:
            QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            QGuiApplication.restoreOverrideCursor()

    def _on_generate(self) -> None:
        key_size = int(self.combo_size.currentText())
        pw = self.gen_pw_entry.text() or None
        self._busy(True)
        try:
            priv_pem, pub_pem = KeyPairManager.generate_keypair(key_size, passphrase=pw)
            self.txt_priv.setPlainText(priv_pem)
            self.txt_pub.setPlainText(pub_pem)
            self.lbl_gen_info.setText(f"{key_size}-bit RSA keypair ready")
            self.lbl_gen_info.setStyleSheet(f"color: {Color.SUCCESS};")
            self.lbl_val_res.setText("")
            if self.app:
                self.app.status(f"{key_size}-bit keypair generated", "success")
        except Exception as exc:
            self.lbl_gen_info.setText(str(exc))
            self.lbl_gen_info.setStyleSheet(f"color: {Color.ERROR};")
            if self.app:
                self.app.status("Keypair generation failed", "error")
        finally:
            self._busy(False)

    def _use_for_generation(self) -> None:
        pem = self._active_private_pem()
        if not pem:
            QMessageBox.warning(
                self,
                "No Private Key",
                "Generate or load a private key before sending it to License Generation.",
            )
            return

        path: str | None = None
        if self._active_source == "generate":
            path = self._last_saved_priv_path
        else:
            text = self.priv_entry.text()
            if text and "memory" not in text.lower() and not text.startswith("Pasted"):
                path = text

        if self.app and hasattr(self.app, "use_signing_key"):
            self.app.use_signing_key(
                path=path,
                pem=pem,
                passphrase=self._active_passphrase(),
            )
        elif self.app and hasattr(self.app, "select_view"):
            self.app.select_view("gen")

    def _save_private(self) -> None:
        pem = self._get_private_pem()
        if not pem:
            QMessageBox.warning(self, "Warning", "Generate a keypair first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Private Key", "", "PEM files (*.pem);;All files (*.*)"
        )
        if path:
            with open(path, "w") as f:
                f.write(pem)
            self._last_saved_priv_path = path
            if self.app:
                self.app.status(f"Private key saved → {path}", "success")

    def _save_public(self) -> None:
        pem = self._get_public_pem()
        if not pem:
            QMessageBox.warning(self, "Warning", "Generate a keypair first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Public Key", "", "PEM files (*.pem);;All files (*.*)"
        )
        if path:
            with open(path, "w") as f:
                f.write(pem)
            if self.app:
                self.app.status(f"Public key saved → {path}", "success")

    def _copy_private(self) -> None:
        pem = self._get_private_pem()
        if pem:
            cb = QApplication.clipboard()
            if cb:
                cb.setText(pem)
            self.lbl_gen_info.setText("Private key copied")
            self.lbl_gen_info.setStyleSheet(f"color: {Color.SUCCESS};")
            if self.app:
                self.app.status("Private key copied to clipboard", "success")
        else:
            QMessageBox.warning(self, "Warning", "Generate a keypair first.")

    def _copy_public(self) -> None:
        pem = self._get_public_pem()
        if pem:
            cb = QApplication.clipboard()
            if cb:
                cb.setText(pem)
            self.lbl_gen_info.setText("Public key copied")
            self.lbl_gen_info.setStyleSheet(f"color: {Color.SUCCESS};")
            if self.app:
                self.app.status("Public key copied to clipboard", "success")
        else:
            QMessageBox.warning(self, "Warning", "Generate a keypair first.")

    def _browse_priv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Private Key", "", "PEM files (*.pem);;All files (*.*)"
        )
        if path:
            self._pasted_pem.pop("priv", None)
            self.priv_entry.setText(path)
            self._last_saved_priv_path = path

    def _browse_pub(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Public Key", "", "PEM files (*.pem);;All files (*.*)"
        )
        if path:
            self._pasted_pem.pop("pub", None)
            self.pub_entry.setText(path)

    def _paste_priv(self) -> None:
        cb = QApplication.clipboard()
        clip = cb.text().strip() if cb else ""
        if not clip:
            QMessageBox.warning(self, "Warning", "Clipboard is empty.")
            return
        if "BEGIN " not in clip:
            QMessageBox.warning(
                self, "Warning", "Clipboard does not appear to contain a PEM key."
            )
            return
        self._pasted_pem["priv"] = clip
        self.priv_entry.setText("Pasted key held in memory (not written to disk)")

    def _paste_pub(self) -> None:
        cb = QApplication.clipboard()
        clip = cb.text().strip() if cb else ""
        if not clip:
            QMessageBox.warning(self, "Warning", "Clipboard is empty.")
            return
        if "BEGIN " not in clip:
            QMessageBox.warning(
                self, "Warning", "Clipboard does not appear to contain a PEM key."
            )
            return
        self._pasted_pem["pub"] = clip
        self.pub_entry.setText("Pasted key held in memory (not written to disk)")

    def _on_validate(self) -> None:
        if self._active_source == "generate":
            priv_pem = self._get_private_pem()
            pub_pem = self._get_public_pem()
        else:
            priv_pem = self._get_load_priv_pem()
            pub_pem = self._get_load_pub_pem()

        if not priv_pem or not pub_pem:
            self._set_result("No keys available in active panel", Color.WARNING)
            return

        pw = self.val_pw_entry.text() or None
        if self._active_source == "generate" and not pw:
            pw = self.gen_pw_entry.text() or None

        self._busy(True)
        try:
            priv_ok = KeyPairManager.validate_private_key(priv_pem, password=pw)
            pub_ok = KeyPairManager.validate_public_key(pub_pem)

            if not priv_ok and not pub_ok:
                self._set_result("Both keys are invalid PEM", Color.ERROR)
                return
            if not priv_ok:
                self._set_result("Private key is invalid PEM", Color.ERROR)
                return
            if not pub_ok:
                self._set_result("Public key is invalid PEM", Color.ERROR)
                return

            if KeyPairManager.verify_keypair(priv_pem, pub_pem, password=pw):
                size = KeyPairManager.get_key_size(priv_pem, password=pw)
                self._set_result(f"Keys match — {size}-bit RSA pair", Color.SUCCESS)
                if self.app:
                    self.app.status(f"Keys validated: {size}-bit pair", "success")
            else:
                self._set_result("Keys do NOT match — different keypairs", Color.ERROR)
                if self.app:
                    self.app.status("Keypair mismatch detected", "error")
        finally:
            self._busy(False)

    def _set_result(self, text: str, color: str) -> None:
        self.lbl_val_res.setText(text)
        self.lbl_val_res.setStyleSheet(
            f"color: {color}; font-weight: bold; font-size: 13px;"
        )
