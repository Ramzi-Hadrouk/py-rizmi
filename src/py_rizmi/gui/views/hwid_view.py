"""Machine Hardware ID generation for PyQt6."""
from __future__ import annotations

from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QFrame, QApplication, QMessageBox, QFormLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication

from ...core.hwid import HardwareIdentifier
from ..theme import Color, button_stylesheet, mono_input_stylesheet


class HWIDTab(QWidget):
    """Generate and copy the SHA-256 machine fingerprint."""

    def __init__(self, app: Any = None) -> None:
        super().__init__()
        self.app = app
        self._build()

    def _build(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        center = QWidget()
        center.setMaximumWidth(640)
        center_layout = QVBoxLayout(center)
        center_layout.setSpacing(16)
        main_layout.addWidget(center)

        lbl_title = QLabel("Machine Hardware Identifier")
        lbl_title.setObjectName("PageTitle")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Generate a unique SHA-256 fingerprint for this machine.\n"
            "Clients send this hash to their license issuer."
        )
        lbl_desc.setObjectName("PageSubtitle")
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setWordWrap(True)
        center_layout.addWidget(lbl_desc)

        btn_gen = QPushButton("Generate Machine ID")
        btn_gen.setFixedHeight(40)
        btn_gen.setMinimumWidth(220)
        btn_gen.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_gen.setStyleSheet(button_stylesheet("primary"))
        btn_gen.setAccessibleName("Generate Machine ID")
        btn_gen.clicked.connect(self._on_generate)
        center_layout.addWidget(btn_gen, alignment=Qt.AlignmentFlag.AlignCenter)

        result_frame = QFrame()
        result_frame.setObjectName("Panel")
        res_layout = QVBoxLayout(result_frame)
        res_layout.setContentsMargins(20, 20, 20, 20)
        res_layout.setSpacing(12)
        center_layout.addWidget(result_frame)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)

        lbl_hash = QLabel("HWID (SHA-256):")
        lbl_hash.setStyleSheet("font-weight: bold;")
        self.hwid_entry = QLineEdit()
        self.hwid_entry.setReadOnly(True)
        self.hwid_entry.setPlaceholderText("Click Generate Machine ID to create a fingerprint")
        self.hwid_entry.setStyleSheet(mono_input_stylesheet())
        self.hwid_entry.setAccessibleName("Hardware ID hash")
        lbl_hash.setBuddy(self.hwid_entry)
        form.addRow(lbl_hash, self.hwid_entry)
        res_layout.addLayout(form)

        act_row = QHBoxLayout()
        btn_copy = QPushButton("Copy HWID")
        btn_copy.setMinimumWidth(120)
        btn_copy.setStyleSheet(button_stylesheet("secondary"))
        btn_copy.setAccessibleName("Copy HWID")
        btn_copy.clicked.connect(self._on_copy)
        act_row.addWidget(btn_copy)

        self.chk_auto = QCheckBox("Auto-copy")
        self.chk_auto.setToolTip("Copy to clipboard automatically after generating")
        act_row.addWidget(self.chk_auto)
        act_row.addStretch()

        self._status_label = QLabel()
        self._status_label.setStyleSheet(f"color: {Color.SUCCESS}; font-weight: bold;")
        act_row.addWidget(self._status_label)
        res_layout.addLayout(act_row)

    def _busy(self, on: bool) -> None:
        if QGuiApplication.instance() is None:
            return
        if on:
            QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            QGuiApplication.restoreOverrideCursor()

    def _on_generate(self) -> None:
        self._busy(True)
        try:
            try:
                hwid = HardwareIdentifier.get_machine_id()
            except Exception:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Failed to generate machine ID. "
                    "The system identifier could not be read.",
                )
                return

            self.hwid_entry.setText(hwid)
            self._status_label.setText("")

            if self.app:
                self.app.status("Machine ID generated", "success")

            if self.chk_auto.isChecked():
                self._do_copy()
        finally:
            self._busy(False)

    def _on_copy(self) -> None:
        hwid = self.hwid_entry.text()
        if not hwid:
            QMessageBox.warning(self, "Warning", "Generate the HWID first.")
            return
        self._do_copy()

    def _do_copy(self) -> None:
        hwid = self.hwid_entry.text()
        cb = QApplication.clipboard()
        if cb is not None:
            cb.setText(hwid)
        self._status_label.setText("Copied to clipboard")
        if self.app:
            self.app.status("HWID copied to clipboard", "success")

    def get_hwid(self) -> str:
        return self.hwid_entry.text()
