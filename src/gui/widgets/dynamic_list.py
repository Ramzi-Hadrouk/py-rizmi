"""Reusable dynamic add/remove list widget (used for features)."""
import customtkinter as ctk
import tkinter as tk
from typing import List
from ..theme import Color


class DynamicListWidget(ctk.CTkFrame):
    """A self-contained widget for managing a list of string values.

    Each row has an Entry plus a remove button.
    A single *Add* button appends a new blank row.
    Uses object references for stable row identification.
    """

    def __init__(self, parent, label: str = "Feature", entry_width: int = 35):
        super().__init__(parent, fg_color="transparent")
        self._label = label
        self._entry_width = entry_width * 10 # roughly converting chars to pixels
        self._rows: list[dict] = []
        self._build()

    # ----- UI -----

    def _build(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._rows_container = ctk.CTkScrollableFrame(self, fg_color=("gray95", "gray13"), corner_radius=8)
        self._rows_container.grid(row=0, column=0, sticky="nsew")

        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        
        ctk.CTkButton(
            btn_bar, text=f"+ Add {self._label}", width=120,
            command=self.add_row,
        ).pack(side="left")

        self.add_row()  # start with one empty row

    def add_row(self, value: str = "") -> None:
        row_frame = ctk.CTkFrame(self._rows_container, fg_color="transparent")
        row_frame.pack(fill="x", pady=5)

        var = ctk.StringVar(value=value)
        entry = ctk.CTkEntry(row_frame, textvariable=var, width=self._entry_width)
        entry.pack(side="left", fill="x", expand=True)

        row = {"frame": row_frame, "var": var, "entry": entry}
        btn = ctk.CTkButton(
            row_frame, text="\u2715", width=30,
            command=lambda r=row: self._remove_row(r),
            fg_color=Color.ERROR, hover_color=Color.ERROR_HOVER
        )
        btn.pack(side="left", padx=(10, 0))

        self._rows.append(row)

    def _remove_row(self, row: dict) -> None:
        if row not in self._rows:
            return
        self._rows.remove(row)
        row["frame"].destroy()
        if not self._rows:
            self.add_row()

    # ----- public API -----

    def get_values(self) -> List[str]:
        return [r["var"].get().strip() for r in self._rows
                if r["var"].get().strip()]

    def set_values(self, values: List[str]) -> None:
        while self._rows:
            row = self._rows.pop(0)
            row["frame"].destroy()
        for val in values:
            self.add_row(val)
        if not self._rows:
            self.add_row()

    def clear(self) -> None:
        self.set_values([])
