"""Tab 1 — Machine Hardware ID generation for PyQt6."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QCheckBox, QFrame, QApplication
)
from PyQt6.QtCore import Qt

from ...core.hwid import HardwareIdentifier
from ..theme import Color

class HWIDTab(QWidget):
    """Generate and copy the SHA-256 machine fingerprint."""
    
    def __init__(self, app=None):
        super().__init__()
        self.app = app
        self._build()
        
    def _build(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Centering container
        center = QWidget()
        center.setMaximumWidth(600)
        center_layout = QVBoxLayout(center)
        center_layout.setSpacing(20)
        main_layout.addWidget(center)
        
        lbl_title = QLabel("Machine Hardware Identifier")
        font = lbl_title.font()
        font.setPointSize(24)
        font.setBold(True)
        lbl_title.setFont(font)
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(lbl_title)
        
        lbl_desc = QLabel(
            "Generate a unique SHA-256 fingerprint for this machine.\n"
            "Send this hash to your license issuer."
        )
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setStyleSheet(f"color: {Color.FG_MUTED};")
        center_layout.addWidget(lbl_desc)
        
        btn_gen = QPushButton("\U0001f5b4  Generate Machine ID")
        btn_gen.setFixedHeight(40)
        btn_gen.setStyleSheet(f"""
            QPushButton {{
                background-color: {Color.ACCENT};
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {Color.ACCENT_HOVER};
            }}
        """)
        btn_gen.clicked.connect(self._on_generate)
        center_layout.addWidget(btn_gen, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Result box
        result_frame = QFrame()
        result_frame.setObjectName("Panel")
        res_layout = QVBoxLayout(result_frame)
        res_layout.setContentsMargins(20, 20, 20, 20)
        res_layout.setSpacing(15)
        center_layout.addWidget(result_frame)
        
        # Raw row
        raw_row = QHBoxLayout()
        lbl_raw = QLabel("Raw Fingerprint:")
        lbl_raw.setFixedWidth(120)
        lbl_raw.setStyleSheet("font-weight: bold;")
        self._raw_value = QLabel("\u2014")
        self._raw_value.setStyleSheet(f"color: {Color.FG_MUTED};")
        raw_row.addWidget(lbl_raw)
        raw_row.addWidget(self._raw_value, stretch=1)
        res_layout.addLayout(raw_row)
        
        # Hash row
        hash_row = QHBoxLayout()
        lbl_hash = QLabel("HWID (SHA-256):")
        lbl_hash.setFixedWidth(120)
        lbl_hash.setStyleSheet("font-weight: bold;")
        self.hwid_entry = QLineEdit()
        self.hwid_entry.setReadOnly(True)
        self.hwid_entry.setStyleSheet(f"background-color: white; color: {Color.TEXT}; font-family: monospace; font-size: 13px; padding: 4px 6px; border: 1px solid {Color.BORDER}; border-radius: 4px;")
        hash_row.addWidget(lbl_hash)
        hash_row.addWidget(self.hwid_entry, stretch=1)
        res_layout.addLayout(hash_row)
        
        # Actions row
        act_row = QHBoxLayout()
        act_row.addSpacing(130) # align with entry
        
        btn_copy = QPushButton("\U0001f4cb  Copy HWID")
        btn_copy.setFixedWidth(120)
        btn_copy.clicked.connect(self._on_copy)
        act_row.addWidget(btn_copy)
        
        self.chk_auto = QCheckBox("Auto-copy")
        act_row.addWidget(self.chk_auto)
        act_row.addStretch()
        res_layout.addLayout(act_row)
        
        self._status_label = QLabel()
        self._status_label.setStyleSheet(f"color: {Color.SUCCESS}; font-weight: bold;")
        act_row.addWidget(self._status_label)
        
    def _on_generate(self) -> None:
        raw = HardwareIdentifier.get_raw_fingerprint()
        hwid = HardwareIdentifier.get_machine_id()
        self._raw_value.setText(raw)
        self._raw_value.setStyleSheet(f"color: {Color.TEXT};")
        self.hwid_entry.setText(hwid)
        self._status_label.setText("")
        
        if self.app:
            self.app.status("Machine ID generated", "success")
            
        if self.chk_auto.isChecked():
            self._do_copy()
            
    def _on_copy(self) -> None:
        hwid = self.hwid_entry.text()
        if not hwid:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Warning", "Generate the HWID first.")
            return
        self._do_copy()
        
    def _do_copy(self) -> None:
        hwid = self.hwid_entry.text()
        QApplication.clipboard().setText(hwid)
        self._status_label.setText("\u2705  Copied to clipboard")
        if self.app:
            self.app.status("HWID copied to clipboard", "success")
            
    def get_hwid(self) -> str:
        return self.hwid_entry.text()
