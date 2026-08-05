"""License Generation view for PyQt6."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFileDialog, QScrollArea, QFrame,
    QCheckBox, QDateEdit, QMessageBox, QApplication, QDialog, QTextEdit,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QGuiApplication

from ...core.license_issuer import LicenseIssuer
from ...models.license_payload import LicensePayload
from ..widgets.dynamic_list import DynamicListWidget
from ..widgets.step_card import StepCard
from ..theme import Color, button_stylesheet, input_stylesheet


class GenerateTab(QWidget):
    """Single-column step-by-step license generation form."""

    def __init__(
        self,
        get_hwid_cb: Callable[[], str] | None = None,
        app: Any = None,
    ) -> None:
        super().__init__()
        self._get_hwid_cb = get_hwid_cb
        self.app = app
        self._required_entries: list[tuple[QLineEdit, str]] = []
        self._private_key_pem: str | None = None
        self._build()

    def set_signing_key(
        self,
        *,
        path: str | None = None,
        pem: str | None = None,
        passphrase: str | None = None,
    ) -> None:
        """Receive a key from Key Management (path and/or in-memory PEM)."""
        self._private_key_pem = pem
        if path:
            self.key_entry.setText(path)
        elif pem:
            self.key_entry.setText("In-memory key from Key Management")
        if passphrase is not None:
            self.pw_entry.setText(passphrase)

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

        title = QLabel("License Generation")
        title.setObjectName("PageTitle")
        self.content_layout.addWidget(title)
        subtitle = QLabel("Fill the steps below, then generate a signed license file.")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        self.content_layout.addWidget(subtitle)

        self._build_step1_key()
        self._build_step2_identity()
        self._build_step3_config()
        self._build_step4_validity()
        self._build_actions()

    def _build_step1_key(self) -> None:
        card = StepCard(step=1, title="Signing Key (Private Key)")
        self.content_layout.addWidget(card)

        row = QHBoxLayout()
        lbl = QLabel("Private Key File:")
        lbl.setStyleSheet(f"font-weight: bold; color: {Color.FG_MUTED};")
        self.key_entry = QLineEdit()
        self.key_entry.setReadOnly(True)
        self.key_entry.setPlaceholderText("No key selected…")
        self.key_entry.setStyleSheet(input_stylesheet())
        self.key_entry.setAccessibleName("Private key file path")
        btn_browse = QPushButton("Browse…")
        btn_browse.setStyleSheet(button_stylesheet("secondary"))
        btn_browse.clicked.connect(self._browse_private_key)

        row.addWidget(lbl)
        row.addWidget(self.key_entry, stretch=1)
        row.addWidget(btn_browse)
        card.body_layout.addLayout(row)

        pw_row = QHBoxLayout()
        lbl_pw = QLabel("Passphrase:")
        lbl_pw.setBuddy(self.key_entry)
        lbl_pw.setStyleSheet(f"font-weight: bold; color: {Color.FG_MUTED};")
        self.pw_entry = QLineEdit()
        self.pw_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_entry.setPlaceholderText("Optional…")
        self.pw_entry.setStyleSheet(input_stylesheet())
        self.pw_entry.setAccessibleName("Private key passphrase")
        pw_row.addWidget(lbl_pw)
        pw_row.addWidget(self.pw_entry, stretch=1)
        card.body_layout.addLayout(pw_row)

        lbl_tip = QLabel(
            "Tip: use Key Management to generate a key, then click "
            "“Use for License Generation”, or browse for a .pem file here."
        )
        lbl_tip.setWordWrap(True)
        lbl_tip.setStyleSheet(f"color: {Color.FG_MUTED}; font-size: 12px;")
        card.body_layout.addWidget(lbl_tip)

    def _build_step2_identity(self) -> None:
        card = StepCard(step=2, title="License Identity")
        self.content_layout.addWidget(card)

        lbl_req = QLabel("* Required fields")
        lbl_req.setStyleSheet(f"color: {Color.ERROR}; font-size: 12px;")
        card.body_layout.addWidget(lbl_req)

        def _add_field(
            label_text: str, required: bool = True, kind: str | None = None
        ) -> QLineEdit:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(120)
            lbl.setStyleSheet("font-weight: bold;")

            if required:
                lbl.setText(
                    f'<b>{label_text}</b> '
                    f'<span style="color:{Color.ERROR};">*</span>'
                )

            entry = QLineEdit()
            entry.setPlaceholderText(f"Enter {label_text.lower()}…")
            entry.setStyleSheet(input_stylesheet())
            entry.setAccessibleName(label_text)
            lbl.setBuddy(entry)

            row.addWidget(lbl)
            row.addWidget(entry, stretch=1)

            if required:
                self._required_entries.append((entry, label_text))

            if kind == "hwid":
                btn_pull = QPushButton("Use Machine ID")
                btn_pull.setToolTip("Copy HWID from the Machine ID panel")
                btn_pull.setStyleSheet(button_stylesheet("secondary"))
                btn_pull.clicked.connect(self._pull_hwid)
                btn_paste = QPushButton("Paste")
                btn_paste.setStyleSheet(button_stylesheet("secondary"))
                btn_paste.clicked.connect(self._paste_hwid)
                row.addWidget(btn_pull)
                row.addWidget(btn_paste)
                self.entry_hwid = entry

            card.body_layout.addLayout(row)
            return entry

        self.entry_client = _add_field("Client Name")
        self.entry_license_id = _add_field("License ID")
        _add_field("Machine HWID", kind="hwid")

    def _build_step3_config(self) -> None:
        card = StepCard(step=3, title="Configuration")
        self.content_layout.addWidget(card)

        grid = QHBoxLayout()
        grid.setSpacing(12)

        def _mini_card(title: str, widget: QWidget) -> None:
            frm = QFrame()
            frm.setObjectName("Panel")
            layout = QVBoxLayout(frm)
            lbl = QLabel(title)
            lbl.setStyleSheet(
                f"font-weight: bold; font-size: 11px; color: {Color.FG_MUTED};"
            )
            layout.addWidget(lbl)
            layout.addWidget(widget)
            grid.addWidget(frm)

        self.entry_max_clients = QLineEdit("10")
        self.entry_max_clients.setStyleSheet(input_stylesheet())
        self.entry_max_clients.setAccessibleName("Max clients")
        _mini_card("Max Clients", self.entry_max_clients)

        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["offline", "online"])
        self.combo_mode.setAccessibleName("License mode")
        self.combo_mode.currentTextChanged.connect(self._on_mode_changed)
        _mini_card("Mode", self.combo_mode)

        self.entry_grace_days = QLineEdit("14")
        self.entry_grace_days.setStyleSheet(input_stylesheet())
        self.entry_grace_days.setAccessibleName("Grace days")
        _mini_card("Grace Days", self.entry_grace_days)

        card.body_layout.addLayout(grid)

        url_row = QHBoxLayout()
        lbl_url = QLabel("Server URL")
        lbl_url.setStyleSheet(f"font-weight: bold; color: {Color.FG_MUTED};")
        self.lbl_url_hint = QLabel("optional")
        self.lbl_url_hint.setStyleSheet(f"font-size: 12px; color: {Color.FG_MUTED};")
        url_row.addWidget(lbl_url)
        url_row.addWidget(self.lbl_url_hint)

        self.entry_server_url = QLineEdit()
        self.entry_server_url.setPlaceholderText(
            "https://…  (required for online mode)"
        )
        self.entry_server_url.setStyleSheet(input_stylesheet())
        self.entry_server_url.setAccessibleName("Server URL")
        url_row.addWidget(self.entry_server_url, stretch=1)
        card.body_layout.addLayout(url_row)

        lbl_feat = QLabel("Features")
        lbl_feat.setStyleSheet(f"font-weight: bold; color: {Color.FG_MUTED};")
        card.body_layout.addWidget(lbl_feat)

        self.features_widget = DynamicListWidget(label="Feature")
        card.body_layout.addWidget(self.features_widget)

        self._on_mode_changed(self.combo_mode.currentText())

    def _on_mode_changed(self, mode: str) -> None:
        online = mode == "online"
        self.lbl_url_hint.setText("required" if online else "optional")
        self.lbl_url_hint.setStyleSheet(
            f"font-size: 12px; color: {Color.ERROR if online else Color.FG_MUTED};"
            if online
            else f"font-size: 12px; color: {Color.FG_MUTED};"
        )

    def _build_step4_validity(self) -> None:
        card = StepCard(step=4, title="Validity Dates")
        self.content_layout.addWidget(card)

        def _date_row(
            label: str, has_days: bool = False
        ) -> tuple[QCheckBox, QLineEdit | None, QDateEdit]:
            frm = QFrame()
            frm.setObjectName("Panel")
            lay = QHBoxLayout(frm)

            lbl_title = QLabel(label)
            lbl_title.setStyleSheet("font-weight: bold; font-size: 12px;")
            lay.addWidget(lbl_title)

            chk_auto = QCheckBox("Auto")
            chk_auto.setChecked(True)
            lay.addWidget(chk_auto)

            entry_days: QLineEdit | None = None
            if has_days:
                lbl_days = QLabel("days:")
                lbl_days.setStyleSheet(f"color: {Color.FG_MUTED};")
                lay.addWidget(lbl_days)
                entry_days = QLineEdit("365")
                entry_days.setFixedWidth(60)
                entry_days.setStyleSheet(input_stylesheet())
                entry_days.setAccessibleName(f"{label} days")
                lay.addWidget(entry_days)

            lbl_or = QLabel("  or pick a date:")
            lbl_or.setStyleSheet(f"color: {Color.FG_MUTED};")
            lay.addWidget(lbl_or)

            picker = QDateEdit(QDate.currentDate())
            picker.setCalendarPopup(True)
            picker.setStyleSheet(input_stylesheet())
            picker.setEnabled(False)
            lay.addWidget(picker)
            lay.addStretch()

            chk_auto.toggled.connect(lambda checked: picker.setEnabled(not checked))
            if entry_days is not None:
                chk_auto.toggled.connect(
                    lambda checked, e=entry_days: e.setEnabled(checked)
                )

            card.body_layout.addWidget(frm)
            return chk_auto, entry_days, picker

        self.iat_auto, self.iat_days, self.iat_picker = _date_row("Issued At (iat)")
        self.exp_auto, self.exp_days, self.exp_picker = _date_row(
            "Expires At (exp)", has_days=True
        )

    def _build_actions(self) -> None:
        act_layout = QVBoxLayout()
        act_layout.setContentsMargins(0, 12, 0, 12)

        btn_gen = QPushButton("Generate License")
        btn_gen.setFixedHeight(44)
        btn_gen.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_gen.setStyleSheet(button_stylesheet("primary") + "font-size: 15px;")
        btn_gen.setAccessibleName("Generate license")
        btn_gen.clicked.connect(self._on_generate)
        act_layout.addWidget(btn_gen)

        sec_row = QHBoxLayout()
        sec_row.setAlignment(Qt.AlignmentFlag.AlignLeft)

        btn_prev = QPushButton("Preview Payload (JSON)")
        btn_prev.setFixedHeight(34)
        btn_prev.setStyleSheet(button_stylesheet("warning"))
        btn_prev.clicked.connect(self._on_preview)

        btn_clear = QPushButton("Clear Form")
        btn_clear.setFixedHeight(34)
        btn_clear.setStyleSheet(button_stylesheet("ghost"))
        btn_clear.clicked.connect(self._on_clear)

        sec_row.addWidget(btn_prev)
        sec_row.addWidget(btn_clear)
        act_layout.addLayout(sec_row)

        self.content_layout.addLayout(act_layout)

    def _browse_private_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Private Key", "", "PEM files (*.pem);;All files (*.*)"
        )
        if path:
            self._private_key_pem = None
            self.key_entry.setText(path)

    def _pull_hwid(self) -> None:
        if self._get_hwid_cb:
            hwid = self._get_hwid_cb()
            if hwid:
                self.entry_hwid.setText(hwid)
                return
        QMessageBox.warning(
            self,
            "No Machine ID",
            "No HWID found. Generate it in Machine ID first, then try again.",
        )
        if self.app and hasattr(self.app, "select_view"):
            self.app.select_view("hwid")

    def _paste_hwid(self) -> None:
        cb = QApplication.clipboard()
        clip = cb.text().strip() if cb else ""
        if not clip:
            QMessageBox.warning(self, "Warning", "Clipboard is empty.")
            return
        self.entry_hwid.setText(clip)

    def _validate_required(self) -> list[str]:
        missing = []
        for entry, label in self._required_entries:
            if not entry.text().strip():
                entry.setStyleSheet(input_stylesheet(error=True))
                missing.append(label)
            else:
                entry.setStyleSheet(input_stylesheet())
        return missing

    def _build_payload(self) -> LicensePayload | None:
        missing = self._validate_required()
        if missing:
            msg = "Please fill in required fields: " + ", ".join(missing)
            QMessageBox.critical(self, "Validation Error", msg)
            if self.app:
                self.app.status(f"Validation failed: {', '.join(missing)}", "error")
            return None

        try:
            max_c = int(self.entry_max_clients.text())
            self.entry_max_clients.setStyleSheet(input_stylesheet())
        except ValueError:
            self.entry_max_clients.setStyleSheet(input_stylesheet(error=True))
            QMessageBox.critical(
                self, "Validation Error", "Max Clients must be a valid integer."
            )
            if self.app:
                self.app.status("Validation failed: Max Clients", "error")
            return None

        try:
            gd = int(self.entry_grace_days.text())
            self.entry_grace_days.setStyleSheet(input_stylesheet())
        except ValueError:
            self.entry_grace_days.setStyleSheet(input_stylesheet(error=True))
            QMessageBox.critical(
                self, "Validation Error", "Grace Days must be a valid integer."
            )
            if self.app:
                self.app.status("Validation failed: Grace Days", "error")
            return None

        if self.combo_mode.currentText() == "online":
            if not self.entry_server_url.text().strip():
                self.entry_server_url.setStyleSheet(input_stylesheet(error=True))
                QMessageBox.critical(
                    self,
                    "Validation Error",
                    "Server URL is required when Mode is online.",
                )
                if self.app:
                    self.app.status("Validation failed: Server URL", "error")
                return None
        self.entry_server_url.setStyleSheet(input_stylesheet())

        payload = LicensePayload(
            client=self.entry_client.text().strip(),
            license_id=self.entry_license_id.text().strip(),
            hwid=self.entry_hwid.text().strip(),
            features=self.features_widget.get_values(),
            max_clients=max_c,
            mode=self.combo_mode.currentText(),
            server_url=self.entry_server_url.text().strip(),
            grace_days=gd,
        )

        if self.iat_auto.isChecked():
            payload.set_auto_iat()
        else:
            qdate = self.iat_picker.date()
            dt = datetime(qdate.year(), qdate.month(), qdate.day(), tzinfo=timezone.utc)
            payload.iat = int(dt.timestamp())

        if self.exp_auto.isChecked():
            try:
                days = int(self.exp_days.text()) if self.exp_days else 365
            except ValueError:
                self.exp_days.setStyleSheet(input_stylesheet(error=True))  # type: ignore[union-attr]
                QMessageBox.critical(
                    self, "Validation Error", "Expiry days must be a valid integer."
                )
                if self.app:
                    self.app.status("Validation failed: Expiry days", "error")
                return None
            if self.exp_days:
                self.exp_days.setStyleSheet(input_stylesheet())
            payload.set_auto_exp(days)
        else:
            qdate = self.exp_picker.date()
            dt = datetime(
                qdate.year(), qdate.month(), qdate.day(), 23, 59, 59, tzinfo=timezone.utc
            )
            payload.exp = int(dt.timestamp())

        return payload

    def _form_is_dirty(self) -> bool:
        return bool(
            self.entry_client.text().strip()
            or self.entry_license_id.text().strip()
            or self.entry_hwid.text().strip()
            or self.entry_server_url.text().strip()
            or self.features_widget.get_values()
        )

    def _on_clear(self) -> None:
        if self._form_is_dirty():
            reply = QMessageBox.question(
                self,
                "Clear Form",
                "Clear all license fields? This cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.entry_client.clear()
        self.entry_license_id.clear()
        self.entry_hwid.clear()
        self.entry_max_clients.setText("10")
        self.combo_mode.setCurrentIndex(0)
        self.entry_server_url.clear()
        self.entry_grace_days.setText("14")
        self.features_widget.clear()

        self.iat_auto.setChecked(True)
        self.iat_picker.setDate(QDate.currentDate())
        self.exp_auto.setChecked(True)
        if self.exp_days:
            self.exp_days.setText("365")
        self.exp_picker.setDate(QDate.currentDate())

        for entry, _ in self._required_entries:
            entry.setStyleSheet(input_stylesheet())

        if self.app:
            self.app.status("Form cleared", "info")

    def _on_preview(self) -> None:
        payload = self._build_payload()
        if payload is None:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Payload Preview — JSON")
        dlg.resize(520, 480)
        lay = QVBoxLayout(dlg)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setStyleSheet(
            f"font-family: monospace; font-size: 13px; {input_stylesheet()}"
        )
        txt.setPlainText(json.dumps(payload.to_dict(), indent=2))
        lay.addWidget(txt)

        buttons = QDialogButtonBox()
        btn_copy = buttons.addButton("Copy JSON", QDialogButtonBox.ButtonRole.ActionRole)
        buttons.addButton(QDialogButtonBox.StandardButton.Close)

        def _copy() -> None:
            cb = QApplication.clipboard()
            if cb:
                cb.setText(txt.toPlainText())
            if self.app:
                self.app.status("Payload JSON copied", "success")

        if btn_copy is not None:
            btn_copy.clicked.connect(_copy)
        buttons.rejected.connect(dlg.reject)
        lay.addWidget(buttons)

        dlg.exec()

    def _busy(self, on: bool) -> None:
        app = QGuiApplication.instance()
        if app is None:
            return
        if on:
            QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            QGuiApplication.restoreOverrideCursor()

    def _on_generate(self) -> None:
        payload = self._build_payload()
        if payload is None:
            return

        key_path = self.key_entry.text().strip()
        if not key_path and not self._private_key_pem:
            QMessageBox.critical(
                self,
                "No Key Selected",
                "Please select a private key file in Step 1, "
                "or use “Use for License Generation” from Key Management.",
            )
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save License File",
            "license.lic",
            "License files (*.lic);;All files (*.*)",
        )
        if not save_path:
            return

        self._busy(True)
        try:
            pw = self.pw_entry.text() or None
            if self._private_key_pem:
                issuer = LicenseIssuer(self._private_key_pem, passphrase=pw)
            else:
                issuer = LicenseIssuer.from_file(key_path, passphrase=pw)
            issuer.issue_to_file(payload, save_path)
            QMessageBox.information(
                self,
                "License Issued",
                f"License written to:\n{save_path}",
            )
            if self.app:
                self.app.status(
                    f"License issued for {payload.client} — {save_path}", "success"
                )
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to generate license:\n{exc}")
            if self.app:
                self.app.status(f"License generation failed: {exc}", "error")
        finally:
            self._busy(False)
