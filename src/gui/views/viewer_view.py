"""Tab 4 — Read-only License Viewer for PyQt6."""
import json
from datetime import datetime, timezone
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QFileDialog, QScrollArea, QFrame, QMessageBox,
    QFormLayout, QTextEdit
)
from PyQt6.QtCore import Qt

from ...core.license_validator import LicenseValidator
from ..theme import Color
from ..widgets.step_card import StepCard

class ViewerTab(QWidget):
    """View and validate a license file using a public key."""
    
    def __init__(self, app=None):
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
        self.content_layout.setSpacing(20)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
        self._build_input_card()
        self._build_results_card()
        
    def _build_input_card(self) -> None:
        card = StepCard(step=1, title="Select Files")
        self.content_layout.addWidget(card)
        
        def _add_file_row(label, attr_prefix):
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(120)
            lbl.setStyleSheet("font-weight: bold;")
            row.addWidget(lbl)
            
            entry = QLineEdit()
            entry.setReadOnly(True)
            row.addWidget(entry, stretch=1)
            setattr(self, f"{attr_prefix}_entry", entry)
            
            btn = QPushButton("Browse…")
            row.addWidget(btn)
            setattr(self, f"{attr_prefix}_btn", btn)
            
            card.body_layout.addLayout(row)
            
        _add_file_row("🔓 Public Key:", "pub")
        self.pub_btn.clicked.connect(self._browse_pub)
        
        _add_file_row("📄 License File:", "lic")
        self.lic_btn.clicked.connect(self._browse_lic)
        
        act_row = QHBoxLayout()
        act_row.addSpacing(130)
        
        btn_view = QPushButton("🔍  Decode & View")
        btn_view.setFixedSize(160, 36)
        btn_view.setStyleSheet(f"""
            QPushButton {{
                background-color: {Color.ACCENT};
                color: white;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Color.ACCENT_HOVER};
            }}
        """)
        btn_view.clicked.connect(self._on_view)
        act_row.addWidget(btn_view)
        
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("font-weight: bold;")
        act_row.addWidget(self.lbl_status)
        act_row.addStretch()
        
        card.body_layout.addSpacing(10)
        card.body_layout.addLayout(act_row)
        
    def _build_results_card(self) -> None:
        card = StepCard(step=2, title="License Data")
        self.content_layout.addWidget(card)
        
        # Form layout for easy key-value alignment
        self.form_widget = QWidget()
        self.form_layout = QFormLayout(self.form_widget)
        self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        self.form_layout.setHorizontalSpacing(20)
        self.form_layout.setVerticalSpacing(10)
        
        # We will dynamically populate this form in _on_view
        card.body_layout.addWidget(self.form_widget)
        
        # JWT raw text
        self.jwt_text = QTextEdit()
        self.jwt_text.setReadOnly(True)
        self.jwt_text.setFixedHeight(120)
        self.jwt_text.setStyleSheet("font-family: monospace; font-size: 11px;")
        card.body_layout.addWidget(self.jwt_text)
        
    def _browse_pub(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Public Key", "", "PEM files (*.pem);;All files (*.*)")
        if path:
            self.pub_entry.setText(path)
            
    def _browse_lic(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select License", "", "License files (*.lic);;All files (*.*)")
        if path:
            self.lic_entry.setText(path)
            
    def _clear_form(self) -> None:
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.jwt_text.clear()
        
    def _add_form_row(self, key: str, value: str, is_mono: bool = False) -> None:
        lbl_k = QLabel(f"{key}:")
        lbl_k.setStyleSheet("font-weight: bold; color: #9ca3af;")
        
        lbl_v = QLineEdit(value)
        lbl_v.setReadOnly(True)
        lbl_v.setStyleSheet("background-color: transparent; border: none;")
        if is_mono:
            lbl_v.setStyleSheet("background-color: transparent; border: none; font-family: monospace;")
            
        self.form_layout.addRow(lbl_k, lbl_v)
        
    def _on_view(self) -> None:
        self._clear_form()
        
        pub_path = self.pub_entry.text()
        lic_path = self.lic_entry.text()
        
        if not pub_path or not lic_path:
            QMessageBox.warning(self, "Missing Files", "Select both a public key and a license file.")
            return
            
        try:
            validator = LicenseValidator.from_file(pub_path)
            with open(lic_path, "r") as f:
                token = f.read().strip()
                
            self.jwt_text.setPlainText(token)
            
            # Use decode_token (no verification checks) just to read data
            data = validator.decode_token(token)
            
            self.lbl_status.setText("✅  Decoded successfully")
            self.lbl_status.setStyleSheet(f"color: {Color.SUCCESS}; font-weight: bold;")
            
            # Format dates
            iat_dt = datetime.fromtimestamp(data.get("iat", 0), tz=timezone.utc)
            exp_dt = datetime.fromtimestamp(data.get("exp", 0), tz=timezone.utc)
            
            now = datetime.now(timezone.utc)
            delta = exp_dt - now
            days_left = delta.days
            
            if days_left < 0:
                exp_str = f"{exp_dt.strftime('%Y-%m-%d %H:%M:%S')} (EXPIRED by {abs(days_left)} days)"
                exp_color = Color.ERROR
            else:
                exp_str = f"{exp_dt.strftime('%Y-%m-%d %H:%M:%S')} ({days_left} days remaining)"
                exp_color = Color.SUCCESS
                
            # Populate form
            self._add_form_row("Client", data.get("client", ""))
            self._add_form_row("License ID", data.get("license_id", ""), is_mono=True)
            self._add_form_row("HWID", data.get("hwid", ""), is_mono=True)
            
            feat = data.get("features", [])
            self._add_form_row("Features", ", ".join(feat) if feat else "None")
            
            self._add_form_row("Mode", data.get("mode", ""))
            self._add_form_row("Max Clients", str(data.get("max_clients", "")))
            self._add_form_row("Grace Days", str(data.get("grace_days", "")))
            self._add_form_row("Server URL", data.get("server_url", "") or "N/A")
            
            self._add_form_row("Issued At", iat_dt.strftime('%Y-%m-%d %H:%M:%S'))
            
            # Custom styled row for Expiry
            lbl_k = QLabel("Expires At:")
            lbl_k.setStyleSheet("font-weight: bold; color: #9ca3af;")
            lbl_v = QLabel(exp_str)
            lbl_v.setStyleSheet(f"color: {exp_color}; font-weight: bold;")
            self.form_layout.addRow(lbl_k, lbl_v)
            
            if self.app:
                self.app.status("License decoded", "info")
                
        except Exception as exc:
            self.lbl_status.setText("❌  Decode failed")
            self.lbl_status.setStyleSheet(f"color: {Color.ERROR}; font-weight: bold;")
            QMessageBox.critical(self, "Error", f"Failed to decode license:\n{exc}")
            if self.app:
                self.app.status("License decode failed", "error")
