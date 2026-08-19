"""License Swap Authorization PyQt6 tab view."""
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

from py_rizmi.core.swap_auth import sign_swap_request
from py_rizmi.gui.theme import Color, button_stylesheet, mono_input_stylesheet
from py_rizmi.models.swap_payload import LicenseSwapPayload


class LicenseSwapTab(QWidget):
    """Sign license swap authorization requests using a local RSA private key."""

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

        lbl_title = QLabel("License Swap Authorization")
        lbl_title.setObjectName("PageTitle")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Locally sign a license swap request file with your RSA private key.\n"
            "The private key is never uploaded or transmitted."
        )
        lbl_desc.setObjectName("PageSubtitle")
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setWordWrap(True)
        center_layout.addWidget(lbl_desc)

        form_frame = QFrame()
        form_frame.setObjectName("Panel")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(14)
        center_layout.addWidget(form_frame)

        grid = QFormLayout()
        grid.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        grid.setHorizontalSpacing(12)

        # 1. Request file row
        lbl_req = QLabel("Swap Request File:")
        lbl_req.setStyleSheet("font-weight: bold;")
        req_row = QHBoxLayout()
        self.txt_req_path = QLineEdit()
        self.txt_req_path.setPlaceholderText("Path to swap request JSON file...")
        self.txt_req_path.setStyleSheet(mono_input_stylesheet())
        btn_req_browse = QPushButton("Browse...")
        btn_req_browse.setStyleSheet(button_stylesheet("secondary"))
        btn_req_browse.clicked.connect(self._browse_request)
        req_row.addWidget(self.txt_req_path)
        req_row.addWidget(btn_req_browse)
        grid.addRow(lbl_req, req_row)

        # 2. Private Key file row
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

        # 3. Passphrase row
        lbl_pass = QLabel("Key Passphrase:")
        lbl_pass.setStyleSheet("font-weight: bold;")
        self.txt_passphrase = QLineEdit()
        self.txt_passphrase.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_passphrase.setPlaceholderText("Optional passphrase for encrypted key")
        self.txt_passphrase.setStyleSheet(mono_input_stylesheet())
        grid.addRow(lbl_pass, self.txt_passphrase)

        form_layout.addLayout(grid)

        # Action button
        btn_sign = QPushButton("Sign License Swap Authorization")
        btn_sign.setFixedHeight(40)
        btn_sign.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sign.setStyleSheet(button_stylesheet("primary"))
        btn_sign.clicked.connect(self._on_sign)
        form_layout.addWidget(btn_sign)

        # Output panel
        out_frame = QFrame()
        out_frame.setObjectName("Panel")
        out_layout = QVBoxLayout(out_frame)
        out_layout.setContentsMargins(20, 20, 20, 20)
        out_layout.setSpacing(10)
        center_layout.addWidget(out_frame)

        lbl_output = QLabel("Signed Authorization Output (.rzswap):")
        lbl_output.setStyleSheet("font-weight: bold;")
        out_layout.addWidget(lbl_output)

        self.txt_output = QTextEdit()
        self.txt_output.setReadOnly(True)
        self.txt_output.setPlaceholderText("Signed swap authorization JSON will appear here after signing.")
        self.txt_output.setStyleSheet(mono_input_stylesheet())
        self.txt_output.setFixedHeight(140)
        out_layout.addWidget(self.txt_output)

        act_row = QHBoxLayout()
        btn_save = QPushButton("Save Authorization File...")
        btn_save.setStyleSheet(button_stylesheet("secondary"))
        btn_save.clicked.connect(self._save_output)
        act_row.addWidget(btn_save)

        self.lbl_status = QLabel()
        self.lbl_status.setStyleSheet(f"color: {Color.SUCCESS}; font-weight: bold;")
        act_row.addWidget(self.lbl_status)
        act_row.addStretch()
        out_layout.addLayout(act_row)

    def _browse_request(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Swap Request File", "", "JSON Files (*.json);;All Files (*)"
        )
        if path:
            self.txt_req_path.setText(path)

    def _browse_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Private Key File", "", "PEM Files (*.pem);;All Files (*)"
        )
        if path:
            self.txt_key_path.setText(path)

    def _on_sign(self) -> None:
        req_path = self.txt_req_path.text().strip()
        key_path = self.txt_key_path.text().strip()
        passphrase = self.txt_passphrase.text() or None

        if not req_path or not key_path:
            QMessageBox.warning(self, "Missing Fields", "Please select both the Request File and Private Key File.")
            return

        try:
            with open(req_path, "r") as f:
                req_data = json.load(f)
            payload_dict = req_data.get("payload", req_data)
            payload = LicenseSwapPayload.from_dict(payload_dict)
        except Exception as exc:
            QMessageBox.critical(self, "Invalid Request File", f"Could not parse request file: {exc}")
            return

        try:
            with open(key_path, "r") as f:
                priv_pem = f.read()
            auth_envelope = sign_swap_request(payload, priv_pem, passphrase=passphrase)
            output_json = json.dumps(auth_envelope, indent=2)
            self.txt_output.setText(output_json)
            self.lbl_status.setText("Signed successfully!")
            if self.app:
                self.app.status("License swap authorization signed successfully", "success")
        except Exception as exc:
            QMessageBox.critical(self, "Signing Failed", f"Failed to sign authorization: {exc}")

    def _save_output(self) -> None:
        content = self.txt_output.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "Empty Content", "Generate a signed authorization first before saving.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Authorization Output", "authorization.rzswap", "Authorization Files (*.rzswap *.rzsig);;JSON Files (*.json)"
        )
        if path:
            try:
                with open(path, "w") as f:
                    f.write(content)
                self.lbl_status.setText("Saved!")
                if self.app:
                    self.app.status(f"Saved authorization to {path}", "success")
            except Exception as exc:
                QMessageBox.critical(self, "Save Failed", f"Could not save file: {exc}")


# Alias for backward compatibility
ReplacementAuthTab = LicenseSwapTab
