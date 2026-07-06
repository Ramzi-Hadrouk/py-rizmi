"""Tab 3 — License Generation for PyQt6."""
import json
from datetime import datetime, timezone
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QComboBox, QFileDialog, QScrollArea, QFrame,
    QCheckBox, QDateEdit, QMessageBox, QApplication, QDialog, QTextEdit
)
from PyQt6.QtCore import Qt, QDate

from ...core.license_issuer import LicenseIssuer
from ...core.license_token import LicensePayload
from ..widgets.dynamic_list import DynamicListWidget
from ..widgets.step_card import StepCard
from ..theme import Color

class GenerateTab(QWidget):
    """Single-column step-by-step license generation form."""
    
    def __init__(self, get_hwid_cb=None, app=None):
        super().__init__()
        self._get_hwid_cb = get_hwid_cb
        self.app = app
        self._required_entries = []
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
        self.content_layout.setSpacing(20)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
        self._build_step1_key()
        self._build_step2_identity()
        self._build_step3_config()
        self._build_step4_validity()
        self._build_actions()
        
    def _build_step1_key(self) -> None:
        card = StepCard(step=1, title="Signing Key  (Private Key)")
        self.content_layout.addWidget(card)
        
        row = QHBoxLayout()
        lbl = QLabel("Private Key File:")
        lbl.setStyleSheet(f"font-weight: bold; color: {Color.FG_MUTED};")
        self.key_entry = QLineEdit()
        self.key_entry.setReadOnly(True)
        self.key_entry.setPlaceholderText("No key selected…")
        btn_browse = QPushButton("Browse…")
        btn_browse.clicked.connect(self._browse_private_key)
        
        row.addWidget(lbl)
        row.addWidget(self.key_entry, stretch=1)
        row.addWidget(btn_browse)
        card.body_layout.addLayout(row)
        
        lbl_tip = QLabel("ℹ  Use the Key Management tab to generate and save a private key first.")
        lbl_tip.setStyleSheet(f"color: {Color.FG_MUTED}; font-size: 11px;")
        card.body_layout.addWidget(lbl_tip)
        
    def _build_step2_identity(self) -> None:
        card = StepCard(step=2, title="License Identity")
        self.content_layout.addWidget(card)
        
        lbl_req = QLabel("* Required fields")
        lbl_req.setStyleSheet(f"color: {Color.ERROR}; font-size: 11px;")
        card.body_layout.addWidget(lbl_req)
        
        def _add_field(label_text, required=True, kind=None):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(120)
            lbl.setStyleSheet("font-weight: bold;")
            
            if required:
                lbl.setText(label_text + " *")
                # Highlight asterisk but QLabel plain text doesn't support rich text easily 
                # unless we use HTML. We'll just use HTML.
                lbl.setText(f'<b>{label_text}</b> <span style="color:{Color.ERROR};">*</span>')
                
            entry = QLineEdit()
            entry.setPlaceholderText(f"Enter {label_text.lower()}…")
            
            row.addWidget(lbl)
            row.addWidget(entry, stretch=1)
            
            if required:
                self._required_entries.append((entry, label_text))
                
            if kind == "hwid":
                btn_tab1 = QPushButton("← Tab 1")
                btn_tab1.clicked.connect(self._pull_hwid)
                btn_paste = QPushButton("Paste")
                btn_paste.clicked.connect(self._paste_hwid)
                row.addWidget(btn_tab1)
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
        
        # Mini-grid (3 columns)
        grid = QHBoxLayout()
        grid.setSpacing(15)
        
        def _mini_card(title, widget):
            frm = QFrame()
            frm.setObjectName("Panel")
            l = QVBoxLayout(frm)
            lbl = QLabel(title)
            lbl.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {Color.FG_MUTED};")
            l.addWidget(lbl)
            l.addWidget(widget)
            grid.addWidget(frm)
            return widget
            
        self.entry_max_clients = QLineEdit("10")
        _mini_card("Max Clients", self.entry_max_clients)
        
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["offline", "online"])
        _mini_card("Mode", self.combo_mode)
        
        self.entry_grace_days = QLineEdit("14")
        _mini_card("Grace Days", self.entry_grace_days)
        
        card.body_layout.addLayout(grid)
        
        # Server URL
        url_row = QHBoxLayout()
        lbl_url = QLabel("Server URL")
        lbl_url.setStyleSheet(f"font-weight: bold; color: {Color.FG_MUTED};")
        lbl_url_opt = QLabel("optional")
        lbl_url_opt.setStyleSheet(f"font-size: 10px; color: {Color.FG_MUTED};")
        url_row.addWidget(lbl_url)
        url_row.addWidget(lbl_url_opt)
        
        self.entry_server_url = QLineEdit()
        self.entry_server_url.setPlaceholderText("https://…  (only needed for online mode)")
        url_row.addWidget(self.entry_server_url, stretch=1)
        card.body_layout.addLayout(url_row)
        
        # Features
        lbl_feat = QLabel("Features")
        lbl_feat.setStyleSheet(f"font-weight: bold; color: {Color.FG_MUTED};")
        card.body_layout.addWidget(lbl_feat)
        
        self.features_widget = DynamicListWidget(label="Feature")
        card.body_layout.addWidget(self.features_widget)
        
    def _build_step4_validity(self) -> None:
        card = StepCard(step=4, title="Validity Dates")
        self.content_layout.addWidget(card)
        
        def _date_row(label, has_days=False):
            frm = QFrame()
            frm.setObjectName("Panel")
            l = QHBoxLayout(frm)
            
            lbl_title = QLabel(label)
            lbl_title.setStyleSheet("font-weight: bold; font-size: 12px;")
            l.addWidget(lbl_title)
            
            chk_auto = QCheckBox("Auto")
            chk_auto.setChecked(True)
            l.addWidget(chk_auto)
            
            entry_days = None
            if has_days:
                lbl_days = QLabel("days:")
                lbl_days.setStyleSheet(f"color: {Color.FG_MUTED};")
                l.addWidget(lbl_days)
                entry_days = QLineEdit("365")
                entry_days.setFixedWidth(60)
                l.addWidget(entry_days)
                
            lbl_or = QLabel("  or pick a date:")
            lbl_or.setStyleSheet(f"color: {Color.FG_MUTED};")
            l.addWidget(lbl_or)
            
            picker = QDateEdit(QDate.currentDate())
            picker.setCalendarPopup(True)
            picker.setEnabled(False) # Auto is checked by default
            l.addWidget(picker)
            l.addStretch()
            
            # Connect toggle
            chk_auto.toggled.connect(lambda checked: picker.setEnabled(not checked))
            if entry_days:
                chk_auto.toggled.connect(lambda checked: entry_days.setEnabled(checked))
                
            card.body_layout.addWidget(frm)
            return chk_auto, entry_days, picker
            
        self.iat_auto, _, self.iat_picker = _date_row("Issued At (iat)")
        self.exp_auto, self.exp_days, self.exp_picker = _date_row("Expires At (exp)", has_days=True)
        
    def _build_actions(self) -> None:
        act_layout = QVBoxLayout()
        act_layout.setContentsMargins(0, 20, 0, 20)
        
        # Primary CTA
        btn_gen = QPushButton("🔐  Generate License")
        btn_gen.setFixedHeight(48)
        btn_gen.setStyleSheet(f"""
            QPushButton {{
                background-color: {Color.ACCENT};
                color: white;
                font-weight: bold;
                font-size: 15px;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: {Color.ACCENT_HOVER};
            }}
        """)
        btn_gen.clicked.connect(self._on_generate)
        act_layout.addWidget(btn_gen)
        
        # Secondary row
        sec_row = QHBoxLayout()
        sec_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        btn_prev = QPushButton("👁  Preview Payload (JSON)")
        btn_prev.setFixedHeight(34)
        btn_prev.setStyleSheet(f"""
            QPushButton {{
                background-color: {Color.WARNING};
                color: white;
            }}
            QPushButton:hover {{
                background-color: {Color.WARNING_HOVER};
            }}
        """)
        btn_prev.clicked.connect(self._on_preview)
        
        btn_clear = QPushButton("🗑  Clear Form")
        btn_clear.setFixedHeight(34)
        btn_clear.clicked.connect(self._on_clear)
        
        sec_row.addWidget(btn_prev)
        sec_row.addWidget(btn_clear)
        act_layout.addLayout(sec_row)
        
        self.content_layout.addLayout(act_layout)
        
    # Helpers
    
    def _browse_private_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Private Key", "", "PEM files (*.pem);;All files (*.*)")
        if path:
            self.key_entry.setText(path)
            
    def _pull_hwid(self) -> None:
        if self._get_hwid_cb:
            hwid = self._get_hwid_cb()
            if hwid:
                self.entry_hwid.setText(hwid)
                return
        QMessageBox.warning(self, "Warning", "No HWID found. Generate it in Tab 1 first.")
        
    def _paste_hwid(self) -> None:
        clip = QApplication.clipboard().text().strip()
        if not clip:
            QMessageBox.warning(self, "Warning", "Clipboard is empty.")
            return
        self.entry_hwid.setText(clip)
        
    def _validate_required(self) -> list[str]:
        missing = []
        for entry, label in self._required_entries:
            if not entry.text().strip():
                entry.setStyleSheet(f"border: 1px solid {Color.ERROR};")
                missing.append(label)
            else:
                entry.setStyleSheet("") # Reset to default
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
        except ValueError:
            max_c = 10
            
        try:
            gd = int(self.entry_grace_days.text())
        except ValueError:
            gd = 14
            
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
                days = int(self.exp_days.text())
            except ValueError:
                days = 365
            payload.set_auto_exp(days)
        else:
            qdate = self.exp_picker.date()
            dt = datetime(qdate.year(), qdate.month(), qdate.day(), 23, 59, 59, tzinfo=timezone.utc)
            payload.exp = int(dt.timestamp())
            
        return payload
        
    # Actions
    
    def _on_clear(self) -> None:
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
        self.exp_days.setText("365")
        self.exp_picker.setDate(QDate.currentDate())
        
        for entry, _ in self._required_entries:
            entry.setStyleSheet("")
            
        if self.app:
            self.app.status("Form cleared", "info")
            
    def _on_preview(self) -> None:
        payload = self._build_payload()
        if payload is None:
            return
            
        dlg = QDialog(self)
        dlg.setWindowTitle("Payload Preview — JSON")
        dlg.resize(520, 480)
        l = QVBoxLayout(dlg)
        
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setStyleSheet("font-family: monospace; font-size: 13px;")
        txt.setPlainText(json.dumps(payload.to_dict(), indent=2))
        l.addWidget(txt)
        
        dlg.exec()
        
    def _on_generate(self) -> None:
        payload = self._build_payload()
        if payload is None:
            return
            
        key_path = self.key_entry.text()
        if not key_path:
            QMessageBox.critical(self, "No Key Selected", "Please select a private key file in Step 1.")
            return
            
        save_path, _ = QFileDialog.getSaveFileName(self, "Save License File", "", "License files (*.lic);;All files (*.*)")
        if not save_path:
            return
            
        try:
            issuer = LicenseIssuer.from_file(key_path)
            issuer.issue_to_file(payload, save_path)
            QMessageBox.information(self, "License Issued ✅", f"License written to:\n{save_path}")
            if self.app:
                self.app.status(f"License issued for {payload.client} — {save_path}", "success")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to generate license:\n{exc}")
            if self.app:
                self.app.status(f"License generation failed: {exc}", "error")
