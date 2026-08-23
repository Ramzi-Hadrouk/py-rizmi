"""License Revocation PyQt6 tab view — publish signed revocation lists."""
from __future__ import annotations

import json
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from py_rizmi.core.revocation import create_revocation_list, sign_revocation_list
from py_rizmi.gui.theme import Color, button_stylesheet, mono_input_stylesheet
from py_rizmi.gui.widgets.dynamic_list import DynamicListWidget


class RevocationTab(QWidget):
    """Publish a signed revocation list (CRL) using a local RSA private key."""

    def __init__(self, app: Any = None) -> None:
        super().__init__()
        self.app = app
        self._build()

    def _build(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        center = QWidget()
        center.setMaximumWidth(720)
        center_layout = QVBoxLayout(center)
        center_layout.setSpacing(16)
        main_layout.addWidget(center)

        lbl_title = QLabel("License Revocation")
        lbl_title.setObjectName("PageTitle")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Publish a signed revocation list (CRL) that rejects specific license IDs.\n"
            "Signing happens locally — the private key is never uploaded or transmitted."
        )
        lbl_desc.setObjectName("PageSubtitle")
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setWordWrap(True)
        center_layout.addWidget(lbl_desc)

        # ── Input panel ──────────────────────────────────────────────
        form_frame = QFrame()
        form_frame.setObjectName("Panel")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(14)
        center_layout.addWidget(form_frame)

        grid = QFormLayout()
        grid.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        grid.setHorizontalSpacing(12)

        # 1. Revoked license IDs
        lbl_ids = QLabel("License IDs to Revoke:")
        lbl_ids.setStyleSheet("font-weight: bold;")
        self.id_list = DynamicListWidget(label="License ID")
        self.id_list.setAccessibleName("License IDs to revoke")
        grid.addRow(lbl_ids, self.id_list)

        # 2. Private key row
        lbl_key = QLabel("Private Key:")
        lbl_key.setStyleSheet("font-weight: bold;")
        key_row = QHBoxLayout()
        self.txt_key_path = QLineEdit()
        self.txt_key_path.setPlaceholderText("Path to RSA private key PEM...")
        self.txt_key_path.setStyleSheet(mono_input_stylesheet())
        btn_key_browse = QPushButton("Browse...")
        btn_key_browse.setStyleSheet(button_stylesheet("secondary"))
        btn_key_browse.clicked.connect(self._browse_key)
        key_row.addWidget(self.txt_key_path)
        key_row.addWidget(btn_key_browse)
        grid.addRow(lbl_key, key_row)

        # 3. Passphrase
        lbl_pass = QLabel("Key Passphrase:")
        lbl_pass.setStyleSheet("font-weight: bold;")
        self.txt_passphrase = QLineEdit()
        self.txt_passphrase.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_passphrase.setPlaceholderText("Optional passphrase for encrypted key")
        self.txt_passphrase.setStyleSheet(mono_input_stylesheet())
        grid.addRow(lbl_pass, self.txt_passphrase)

        # 4. Next update (hours)
        lbl_next = QLabel("Next Update (hours):")
        lbl_next.setStyleSheet("font-weight: bold;")
        self.txt_next_update = QLineEdit("24")
        self.txt_next_update.setStyleSheet(mono_input_stylesheet())
        self.txt_next_update.setToolTip(
            "Advisory refresh horizon embedded in the list. Validators keep\n"
            "accepting the last known list after this passes (offline-safe)."
        )
        grid.addRow(lbl_next, self.txt_next_update)

        form_layout.addLayout(grid)

        btn_publish = QPushButton("Sign Revocation List")
        btn_publish.setFixedHeight(40)
        btn_publish.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_publish.setStyleSheet(button_stylesheet("primary"))
        btn_publish.clicked.connect(self._on_publish)
        form_layout.addWidget(btn_publish)

        # ── Output panel ─────────────────────────────────────────────
        out_frame = QFrame()
        out_frame.setObjectName("Panel")
        out_layout = QVBoxLayout(out_frame)
        out_layout.setContentsMargins(20, 20, 20, 20)
        out_layout.setSpacing(10)
        center_layout.addWidget(out_frame)

        lbl_output = QLabel("Signed Revocation List (JSON):")
        lbl_output.setStyleSheet("font-weight: bold;")
        out_layout.addWidget(lbl_output)

        self.txt_output = QTextEdit()
        self.txt_output.setReadOnly(True)
        self.txt_output.setPlaceholderText(
            "Signed CRL JSON will appear here after signing. Distribute it to your apps."
        )
        self.txt_output.setStyleSheet(mono_input_stylesheet())
        self.txt_output.setFixedHeight(160)
        out_layout.addWidget(self.txt_output)

        act_row = QHBoxLayout()
        btn_save = QPushButton("Save Revocation List...")
        btn_save.setStyleSheet(button_stylesheet("secondary"))
        btn_save.clicked.connect(self._save_output)
        act_row.addWidget(btn_save)

        self.lbl_status = QLabel()
        self.lbl_status.setStyleSheet(f"color: {Color.SUCCESS}; font-weight: bold;")
        act_row.addWidget(self.lbl_status)
        act_row.addStretch()
        out_layout.addLayout(act_row)

    # ── handlers ─────────────────────────────────────────────────────

    def _browse_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Private Key File", "", "PEM Files (*.pem);;All Files (*)"
        )
        if path:
            self.txt_key_path.setText(path)

    def _get_ids(self) -> list[str]:
        return [item.strip() for item in self.id_list.get_values() if item.strip()]

    def _on_publish(self) -> None:
        ids = self._get_ids()
        key_path = self.txt_key_path.text().strip()
        passphrase = self.txt_passphrase.text() or None

        if not key_path:
            QMessageBox.warning(self, "Missing Field", "Please select a Private Key file.")
            return

        if not ids:
            confirm = QMessageBox.question(
                self,
                "Empty Revocation List",
                "No license IDs entered — this publishes a CLEAN list that\n"
                "un-revokes everything previously listed.\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return

        try:
            next_hours = int(self.txt_next_update.text().strip())
            if next_hours <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(
                self, "Invalid Input", "Next Update (hours) must be a positive integer."
            )
            return

        try:
            payload = create_revocation_list(ids, next_update_hours=next_hours)
            with open(key_path, "r") as f:
                priv_pem = f.read()
            envelope = sign_revocation_list(payload, priv_pem, passphrase=passphrase)
        except Exception as exc:
            QMessageBox.critical(self, "Signing Failed", f"Failed to sign revocation list: {exc}")
            return

        self.txt_output.setText(json.dumps(envelope, indent=2))
        summary = ", ".join(ids) if ids else "clean list (nothing revoked)"
        self.lbl_status.setText("Signed successfully!")
        if self.app:
            self.app.status(f"Revocation list signed: {summary}", "success")

    def _save_output(self) -> None:
        content = self.txt_output.toPlainText().strip()
        if not content:
            QMessageBox.warning(
                self, "Empty Content", "Sign a revocation list first before saving."
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Revocation List",
            "revocation_list.json",
            "JSON Files (*.json);;All Files (*)",
        )
        if path:
            try:
                with open(path, "w") as f:
                    f.write(content)
                self.lbl_status.setText("Saved!")
                if self.app:
                    self.app.status(f"Saved revocation list to {path}", "success")
            except Exception as exc:
                QMessageBox.critical(self, "Save Failed", f"Could not save file: {exc}")
