"""Read-only License Viewer for PyQt6."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QScrollArea, QFrame, QMessageBox,
    QFormLayout, QTextEdit, QSizePolicy, QLayoutItem,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication

from ...core.license_validator import ERROR_MESSAGES, LicenseValidator
from ..theme import Color, button_stylesheet, input_stylesheet, mono_input_stylesheet
from ..widgets.step_card import StepCard


class ViewerTab(QWidget):
    """View and validate a license file using a public key."""

    pub_entry: QLineEdit
    lic_entry: QLineEdit
    pub_btn: QPushButton
    lic_btn: QPushButton

    def __init__(self, app: Any = None) -> None:
        super().__init__()
        self.app = app
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
        self.content_layout.setSpacing(16)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        title = QLabel("License Viewer")
        title.setObjectName("PageTitle")
        self.content_layout.addWidget(title)
        subtitle = QLabel(
            "Decode a license file and check signature / expiry "
            "(HWID check skipped so issuers can inspect any machine’s license)."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        self.content_layout.addWidget(subtitle)

        self._build_input_card()
        self._build_results_card()

    def _build_input_card(self) -> None:
        card = StepCard(step=1, title="Select Files")
        self.content_layout.addWidget(card)

        def _add_file_row(label: str, attr_prefix: str) -> None:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(120)
            lbl.setStyleSheet("font-weight: bold;")
            row.addWidget(lbl)

            entry = QLineEdit()
            entry.setReadOnly(True)
            entry.setStyleSheet(input_stylesheet())
            entry.setAccessibleName(label)
            row.addWidget(entry, stretch=1)
            setattr(self, f"{attr_prefix}_entry", entry)

            btn = QPushButton("Browse…")
            btn.setStyleSheet(button_stylesheet("secondary"))
            row.addWidget(btn)
            setattr(self, f"{attr_prefix}_btn", btn)

            card.body_layout.addLayout(row)

        _add_file_row("Public Key:", "pub")
        self.pub_btn.clicked.connect(self._browse_pub)

        _add_file_row("License File:", "lic")
        self.lic_btn.clicked.connect(self._browse_lic)

        act_row = QHBoxLayout()
        btn_view = QPushButton("Decode & Verify")
        btn_view.setMinimumHeight(36)
        btn_view.setMinimumWidth(160)
        btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_view.setStyleSheet(button_stylesheet("primary"))
        btn_view.setAccessibleName("Decode and verify license")
        btn_view.clicked.connect(self._on_view)
        act_row.addWidget(btn_view)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("font-weight: bold;")
        act_row.addWidget(self.lbl_status)
        act_row.addStretch()

        card.body_layout.addSpacing(8)
        card.body_layout.addLayout(act_row)

    def _build_results_card(self) -> None:
        card = StepCard(step=2, title="License Data")
        self.content_layout.addWidget(card)

        self.lbl_verify = QLabel(
            "Select a public key and license file, then click Decode & Verify."
        )
        self.lbl_verify.setObjectName("EmptyState")
        self.lbl_verify.setWordWrap(True)
        self.lbl_verify.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.body_layout.addWidget(self.lbl_verify)

        self.form_widget = QWidget()
        self.form_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum
        )
        self.form_layout = QFormLayout(self.form_widget)
        self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        self.form_layout.setHorizontalSpacing(20)
        self.form_layout.setVerticalSpacing(10)
        card.body_layout.addWidget(self.form_widget)

        self.jwt_text = QTextEdit()
        self.jwt_text.setReadOnly(True)
        self.jwt_text.setMinimumHeight(100)
        self.jwt_text.setPlaceholderText("Raw license token appears here after decode.")
        self.jwt_text.setStyleSheet(
            f"font-family: monospace; font-size: 11px; {input_stylesheet()}"
        )
        self.jwt_text.setAccessibleName("Raw license token")
        card.body_layout.addWidget(self.jwt_text, stretch=1)

    def _browse_pub(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Public Key", "", "PEM files (*.pem);;All files (*.*)"
        )
        if path:
            self.pub_entry.setText(path)

    def _browse_lic(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select License", "", "License files (*.lic);;All files (*.*)"
        )
        if path:
            self.lic_entry.setText(path)

    def _clear_form(self) -> None:
        while self.form_layout.count():
            item: QLayoutItem | None = self.form_layout.takeAt(0)
            if item is not None and item.widget() is not None:
                item.widget().deleteLater()  # type: ignore[union-attr]
        self.jwt_text.clear()

    def _set_verify_banner(self, text: str, kind: str) -> None:
        colors = {
            "success": (Color.SUCCESS, Color.SUCCESS_LIGHT),
            "error": (Color.ERROR, Color.ERROR_LIGHT),
            "warning": (Color.WARNING, Color.WARNING_LIGHT),
            "info": (Color.FG_MUTED, Color.PANEL_BG),
        }
        fg, bg = colors.get(kind, colors["info"])
        self.lbl_verify.setObjectName("VerifyBanner")
        self.lbl_verify.setText(text)
        self.lbl_verify.setStyleSheet(
            f"color: {fg}; background-color: {bg}; "
            f"font-weight: bold; font-size: 13px; padding: 10px 12px; border-radius: 6px;"
        )

    def _add_form_row(self, key: str, value: str, is_mono: bool = False) -> None:
        lbl_k = QLabel(f"{key}:")
        lbl_k.setStyleSheet(f"font-weight: bold; color: {Color.FG_MUTED};")

        lbl_v = QLineEdit(value)
        lbl_v.setReadOnly(True)
        lbl_v.setStyleSheet(
            mono_input_stylesheet() if is_mono else input_stylesheet()
        )
        self.form_layout.addRow(lbl_k, lbl_v)

    def _busy(self, on: bool) -> None:
        if QGuiApplication.instance() is None:
            return
        if on:
            QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            QGuiApplication.restoreOverrideCursor()

    def _on_view(self) -> None:
        self._clear_form()

        pub_path = self.pub_entry.text()
        lic_path = self.lic_entry.text()

        if not pub_path or not lic_path:
            QMessageBox.warning(
                self, "Missing Files", "Select both a public key and a license file."
            )
            return

        self._busy(True)
        try:
            validator = LicenseValidator.from_file(pub_path)
            with open(lic_path, "r") as f:
                token = f.read().strip()

            self.jwt_text.setPlainText(token)

            # Decode for display (signature must match public key)
            data = validator.decode_token(token)

            # Full validation without HWID (issuer inspecting any client license)
            verify_kind = "success"
            verify_text = "Signature valid — license OK"
            try:
                payload = validator.validate(token, check_hwid=False)
                if getattr(payload, "in_grace_period", False):
                    verify_kind = "warning"
                    verify_text = "Signature valid — license is in grace period"
            except ValueError as exc:
                code = str(exc)
                verify_text = ERROR_MESSAGES.get(code, code)
                verify_kind = "warning" if code == "expired" else "error"

            self._set_verify_banner(verify_text, verify_kind)

            self.lbl_status.setText("Decoded successfully")
            self.lbl_status.setStyleSheet(
                f"color: {Color.SUCCESS}; font-weight: bold;"
            )

            iat_dt = datetime.fromtimestamp(data.get("iat", 0), tz=timezone.utc)
            exp_dt = datetime.fromtimestamp(data.get("exp", 0), tz=timezone.utc)

            now = datetime.now(timezone.utc)
            days_left = (exp_dt - now).days

            if days_left < 0:
                exp_str = (
                    f"{exp_dt.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"(EXPIRED by {abs(days_left)} days)"
                )
                exp_color = Color.ERROR
            else:
                exp_str = (
                    f"{exp_dt.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"({days_left} days remaining)"
                )
                exp_color = Color.SUCCESS

            self._add_form_row("Client", data.get("client", ""))
            self._add_form_row("License ID", data.get("license_id", ""), is_mono=True)
            self._add_form_row("HWID", data.get("hwid", ""), is_mono=True)

            feat = data.get("features", [])
            self._add_form_row("Features", ", ".join(feat) if feat else "None")

            self._add_form_row("Mode", data.get("mode", ""))
            self._add_form_row("Max Clients", str(data.get("max_clients", "")))
            self._add_form_row("Grace Days", str(data.get("grace_days", "")))
            self._add_form_row("Server URL", data.get("server_url", "") or "N/A")

            self._add_form_row("Issued At", iat_dt.strftime("%Y-%m-%d %H:%M:%S"))

            lbl_k = QLabel("Expires At:")
            lbl_k.setStyleSheet(f"font-weight: bold; color: {Color.FG_MUTED};")
            lbl_v = QLabel(exp_str)
            lbl_v.setStyleSheet(f"color: {exp_color}; font-weight: bold;")
            self.form_layout.addRow(lbl_k, lbl_v)

            if self.app:
                self.app.status("License decoded", "info")

        except Exception as exc:
            self.lbl_status.setText("Decode failed")
            self.lbl_status.setStyleSheet(f"color: {Color.ERROR}; font-weight: bold;")
            self._set_verify_banner(f"Failed to decode license: {exc}", "error")
            QMessageBox.critical(self, "Error", f"Failed to decode license:\n{exc}")
            if self.app:
                self.app.status("License decode failed", "error")
        finally:
            self._busy(False)
