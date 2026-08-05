"""Reusable dynamic add/remove list widget for PyQt6."""
from __future__ import annotations

from typing import List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
)
from PyQt6.QtCore import Qt

from ..theme import button_stylesheet, input_stylesheet


class DynamicListWidget(QWidget):
    """Manage a list of string values without nested scroll areas.

    Parent views already scroll; rows grow in-place for predictable desktop UX.
    """

    def __init__(self, label: str = "Feature", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._label = label
        self._rows: list[dict[str, QWidget]] = []
        self._build()

    def _build(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(5)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.addWidget(self.container)

        self.btn_add = QPushButton(f"+ Add {self._label}")
        self.btn_add.setMinimumWidth(120)
        self.btn_add.setStyleSheet(button_stylesheet("secondary"))
        self.btn_add.setAccessibleName(f"Add {self._label}")
        main_layout.addWidget(self.btn_add, alignment=Qt.AlignmentFlag.AlignLeft)
        self.btn_add.clicked.connect(lambda: self.add_row())

    def add_row(self, value: str = "") -> None:
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        entry = QLineEdit(value)
        entry.setMinimumWidth(200)
        entry.setPlaceholderText(f"{self._label} name")
        entry.setStyleSheet(input_stylesheet())
        entry.setAccessibleName(self._label)
        row_layout.addWidget(entry)

        btn_rm = QPushButton("Remove")
        btn_rm.setMinimumHeight(28)
        btn_rm.setStyleSheet(button_stylesheet("ghost"))
        btn_rm.setAccessibleName(f"Remove {self._label}")

        row_dict: dict[str, QWidget] = {"widget": row_widget, "entry": entry}
        btn_rm.clicked.connect(lambda: self._remove_row(row_dict))
        row_layout.addWidget(btn_rm)

        self.container_layout.addWidget(row_widget)
        self._rows.append(row_dict)

    def _remove_row(self, row: dict[str, QWidget]) -> None:
        if row not in self._rows:
            return
        self._rows.remove(row)
        row["widget"].setParent(None)
        row["widget"].deleteLater()

    def get_values(self) -> List[str]:
        return [
            r["entry"].text().strip()  # type: ignore[attr-defined]
            for r in self._rows
            if r["entry"].text().strip()  # type: ignore[attr-defined]
        ]

    def set_values(self, values: List[str]) -> None:
        while self._rows:
            row = self._rows.pop(0)
            row["widget"].setParent(None)
            row["widget"].deleteLater()
        for val in values:
            self.add_row(val)

    def clear(self) -> None:
        self.set_values([])
