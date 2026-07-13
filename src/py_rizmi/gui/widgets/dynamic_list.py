"""Reusable dynamic add/remove list widget for PyQt6."""
from typing import List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from ..theme import Color

class DynamicListWidget(QWidget):
    """A self-contained widget for managing a list of string values.
    
    Each row has an Entry plus a remove button.
    A single *Add* button appends a new blank row.
    """
    
    def __init__(self, label: str = "Feature", parent=None):
        super().__init__(parent)
        self._label = label
        self._rows = []
        self._build()
        
    def _build(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)
        
        # Scroll area for rows
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background-color: transparent;")
        
        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(5)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.container)
        main_layout.addWidget(self.scroll_area)
        
        # Add button
        self.btn_add = QPushButton(f"+ Add {self._label}")
        self.btn_add.setFixedWidth(120)
        main_layout.addWidget(self.btn_add, alignment=Qt.AlignmentFlag.AlignLeft)
        self.btn_add.clicked.connect(lambda: self.add_row())
        
        self.add_row()
        
    def add_row(self, value: str = "") -> None:
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)
        
        entry = QLineEdit(value)
        entry.setMinimumWidth(250)
        entry.setStyleSheet(f"background-color: white; color: {Color.TEXT}; padding: 4px 6px; border: 1px solid {Color.BORDER}; border-radius: 4px;")
        row_layout.addWidget(entry)
        
        btn_rm = QPushButton("\u2715")
        btn_rm.setFixedSize(30, 30)
        btn_rm.setStyleSheet(f"""
            QPushButton {{
                background-color: {Color.ERROR};
                color: white;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {Color.ERROR_HOVER};
            }}
        """)
        
        row_dict = {"widget": row_widget, "entry": entry}
        btn_rm.clicked.connect(lambda: self._remove_row(row_dict))
        row_layout.addWidget(btn_rm)
        
        self.container_layout.addWidget(row_widget)
        self._rows.append(row_dict)
        
    def _remove_row(self, row: dict) -> None:
        if row not in self._rows:
            return
        self._rows.remove(row)
        row["widget"].setParent(None)
        row["widget"].deleteLater()
        
        if not self._rows:
            self.add_row()
            
    def get_values(self) -> List[str]:
        return [r["entry"].text().strip() for r in self._rows if r["entry"].text().strip()]
        
    def set_values(self, values: List[str]) -> None:
        while self._rows:
            row = self._rows.pop(0)
            row["widget"].setParent(None)
            row["widget"].deleteLater()
        for val in values:
            self.add_row(val)
        if not self._rows:
            self.add_row()
            
    def clear(self) -> None:
        self.set_values([])
