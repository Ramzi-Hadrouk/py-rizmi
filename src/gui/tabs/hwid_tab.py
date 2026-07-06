"""Tab 1 — Machine Hardware ID generation (Task 4.3)."""
import tkinter as tk
from tkinter import messagebox, ttk

from ...core.hwid import HardwareIdentifier
from ..theme import Color, Font, Pad


class HWIDTab(ttk.Frame):
    """Generate and copy the SHA-256 machine fingerprint."""

    def __init__(self, parent, app=None):
        super().__init__(parent)
        self.app = app
        self.hwid_var = tk.StringVar()
        self._build()

    # ----- UI -----

    def _build(self) -> None:
        ttk.Label(
            self, text="Machine Hardware Identifier",
            style="Heading.TLabel",
        ).pack(pady=(Pad.XXL, Pad.SM))

        ttk.Label(
            self,
            text=(
                "Generate a unique SHA-256 fingerprint for this machine.\n"
                "Send this hash to your license issuer."
            ),
            justify="center",
        ).pack(pady=(0, Pad.XL))

        ttk.Button(
            self, text="\U0001f5b4  Generate Machine ID",
            command=self._on_generate,
        ).pack(pady=Pad.MD)

        result = ttk.LabelFrame(self, text="Result", padding=Pad.XL)
        result.pack(fill="x", padx=40, pady=Pad.MD)
        result.columnconfigure(1, weight=1)

        ttk.Label(result, text="Raw Fingerprint:").grid(
            row=0, column=0, sticky="w", pady=Pad.SM
        )
        self._raw_label = ttk.Label(result, text="\u2014", foreground=Color.DISABLED)
        self._raw_label.grid(row=0, column=1, sticky="w", pady=Pad.SM, padx=Pad.MD)

        ttk.Label(result, text="HWID (SHA-256):").grid(
            row=1, column=0, sticky="w", pady=Pad.SM
        )
        ttk.Entry(
            result, textvariable=self.hwid_var,
            state="readonly", width=70,
        ).grid(row=1, column=1, sticky="ew", pady=Pad.SM, padx=Pad.MD)

        btn_row = ttk.Frame(result)
        btn_row.grid(row=2, column=1, sticky="w", pady=Pad.MD, padx=Pad.MD)
        ttk.Button(
            btn_row, text="\U0001f4cb  Copy HWID", command=self._on_copy,
        ).pack(side="left", padx=(0, Pad.MD))
        self._auto_copy_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            btn_row, text="Auto-copy", variable=self._auto_copy_var,
        ).pack(side="left")
        self._status_label = ttk.Label(result, text="", font=Font.SMALL)
        self._status_label.grid(row=3, column=1, sticky="w", padx=Pad.MD)

    # ----- actions -----

    def _on_generate(self) -> None:
        raw = HardwareIdentifier.get_raw_fingerprint()
        hwid = HardwareIdentifier.get_machine_id()
        self._raw_label.config(text=raw, foreground=Color.FG)
        self.hwid_var.set(hwid)
        self._status_label.config(text="")
        if self.app:
            self.app.status("Machine ID generated", "success")
        if self._auto_copy_var.get():
            self._do_copy()

    def _on_copy(self) -> None:
        hwid = self.hwid_var.get()
        if not hwid:
            messagebox.showwarning("Warning", "Generate the HWID first.")
            return
        self._do_copy()

    def _do_copy(self) -> None:
        hwid = self.hwid_var.get()
        self.clipboard_clear()
        self.clipboard_append(hwid)
        self._status_label.config(
            text="\u2705  Copied to clipboard", foreground=Color.SUCCESS
        )
        if self.app:
            self.app.status("HWID copied to clipboard", "success")

    def get_hwid(self) -> str:
        """Allow other tabs to pull the current HWID value."""
        return self.hwid_var.get()
