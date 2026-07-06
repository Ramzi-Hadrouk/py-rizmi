"""Tab 1 — Machine Hardware ID generation (Task 4.3)."""
import tkinter as tk
from tkinter import messagebox, ttk

from ...core.hwid import HardwareIdentifier


class HWIDTab(ttk.Frame):
    """Generate and copy the SHA-256 machine fingerprint."""

    def __init__(self, parent):
        super().__init__(parent)
        self.hwid_var = tk.StringVar()
        self._build()

    # ----- UI -----

    def _build(self) -> None:
        ttk.Label(
            self, text="Machine Hardware Identifier",
            font=("TkDefaultFont", 14, "bold"),
        ).pack(pady=(24, 4))

        ttk.Label(
            self,
            text=(
                "Generate a unique SHA-256 fingerprint for this machine.\n"
                "Send this hash to your license issuer."
            ),
            justify="center",
        ).pack(pady=(0, 20))

        ttk.Button(
            self, text="Generate Machine ID",
            command=self._on_generate,
        ).pack(pady=8)

        result = ttk.LabelFrame(self, text="Result", padding=16)
        result.pack(fill="x", padx=40, pady=8)

        ttk.Label(result, text="Raw Fingerprint:").grid(
            row=0, column=0, sticky="w", pady=4
        )
        self._raw_label = ttk.Label(result, text="—", foreground="gray")
        self._raw_label.grid(row=0, column=1, sticky="w", pady=4, padx=10)

        ttk.Label(result, text="HWID (SHA-256):").grid(
            row=1, column=0, sticky="w", pady=4
        )
        ttk.Entry(
            result, textvariable=self.hwid_var,
            state="readonly", width=70,
        ).grid(row=1, column=1, sticky="w", pady=4, padx=10)

        ttk.Button(
            result, text="Copy HWID", command=self._on_copy,
        ).grid(row=2, column=1, sticky="w", pady=10, padx=10)

    # ----- actions -----

    def _on_generate(self) -> None:
        raw = HardwareIdentifier.get_raw_fingerprint()
        hwid = HardwareIdentifier.get_machine_id()
        self._raw_label.config(text=raw)
        self.hwid_var.set(hwid)

    def _on_copy(self) -> None:
        hwid = self.hwid_var.get()
        if not hwid:
            messagebox.showwarning("Warning", "Generate the HWID first.")
            return
        self.clipboard_clear()
        self.clipboard_append(hwid)
        messagebox.showinfo("Copied", "HWID copied to clipboard.")

    def get_hwid(self) -> str:
        """Allow other tabs to pull the current HWID value."""
        return self.hwid_var.get()
