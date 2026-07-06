"""Reusable dynamic add/remove list widget (used for features)."""
import tkinter as tk
from tkinter import ttk
from typing import List


class DynamicListWidget(ttk.Frame):
    """A self-contained widget for managing a list of string values.

    Each row has an Entry plus a remove button.
    A single *Add* button appends a new blank row.
    """

    def __init__(self, parent, label: str = "Feature", entry_width: int = 35):
        super().__init__(parent)
        self._label = label
        self._entry_width = entry_width
        self._rows: list[tuple[ttk.Frame, tk.StringVar, ttk.Entry]] = []
        self._build()

    # ----- UI -----

    def _build(self) -> None:
        self._rows_container = ttk.Frame(self)
        self._rows_container.pack(fill="x", expand=True)

        btn_bar = ttk.Frame(self)
        btn_bar.pack(fill="x", pady=(6, 0))
        ttk.Button(
            btn_bar, text=f"+ Add {self._label}", width=15,
            command=self.add_row,
        ).pack(side="left")

        self.add_row()  # start with one empty row

    def add_row(self, value: str = "") -> None:
        row_frame = ttk.Frame(self._rows_container)
        row_frame.pack(fill="x", pady=2)

        var = tk.StringVar(value=value)
        entry = ttk.Entry(row_frame, textvariable=var, width=self._entry_width)
        entry.pack(side="left", fill="x", expand=True)

        idx = len(self._rows)
        btn = ttk.Button(
            row_frame, text="✕", width=3,
            command=lambda i=idx: self._remove_by_index(i),
        )
        btn.pack(side="left", padx=(4, 0))

        self._rows.append((row_frame, var, entry))

    def _remove_by_index(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._rows):
            return
        frame, _, _ = self._rows.pop(idx)
        frame.destroy()
        if not self._rows:
            self.add_row()

    # ----- public API -----

    def get_values(self) -> List[str]:
        return [v.get().strip() for _, v, _ in self._rows if v.get().strip()]

    def set_values(self, values: List[str]) -> None:
        while self._rows:
            self._remove_by_index(0)
        for val in values:
            self.add_row(val)
        if not self._rows:
            self.add_row()

    def clear(self) -> None:
        self.set_values([])
