"""Tab 1 — Machine Hardware ID generation (Task 4.3)."""
import customtkinter as ctk
import tkinter as tk
from CTkMessagebox import CTkMessagebox

from ...core.hwid import HardwareIdentifier
from ..theme import Color

class HWIDTab(ctk.CTkFrame):
    """Generate and copy the SHA-256 machine fingerprint."""

    def __init__(self, parent, app=None):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.hwid_var = tk.StringVar()
        self._build()

    # ----- UI -----

    def _build(self) -> None:
        # Centering frame
        center_frame = ctk.CTkFrame(self, fg_color="transparent")
        center_frame.pack(expand=True, fill="both", padx=40, pady=40)

        ctk.CTkLabel(
            center_frame, text="Machine Hardware Identifier",
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            center_frame,
            text=(
                "Generate a unique SHA-256 fingerprint for this machine.\n"
                "Send this hash to your license issuer."
            ),
            justify="center",
            text_color="gray50"
        ).pack(pady=(0, 30))

        ctk.CTkButton(
            center_frame, text="\U0001f5b4  Generate Machine ID",
            command=self._on_generate,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        ).pack(pady=10)

        # Result box
        result = ctk.CTkFrame(center_frame, fg_color=("gray95", "gray13"), corner_radius=8)
        result.pack(fill="x", pady=20)
        result.columnconfigure(1, weight=1)

        ctk.CTkLabel(result, text="Raw Fingerprint:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", pady=15, padx=(20, 10)
        )
        self._raw_label = ctk.CTkLabel(result, text="\u2014", text_color="gray50")
        self._raw_label.grid(row=0, column=1, sticky="w", pady=15, padx=10)

        ctk.CTkLabel(result, text="HWID (SHA-256):", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=0, sticky="w", pady=15, padx=(20, 10)
        )
        self.hwid_entry = ctk.CTkEntry(
            result, textvariable=self.hwid_var,
            state="readonly", width=400,
            font=ctk.CTkFont(family="Courier", size=13)
        )
        self.hwid_entry.grid(row=1, column=1, sticky="ew", pady=15, padx=10)

        btn_row = ctk.CTkFrame(result, fg_color="transparent")
        btn_row.grid(row=2, column=1, sticky="w", pady=(5, 20), padx=10)
        
        ctk.CTkButton(
            btn_row, text="\U0001f4cb  Copy HWID", command=self._on_copy,
            width=120
        ).pack(side="left", padx=(0, 20))
        
        self._auto_copy_var = ctk.StringVar(value="off")
        ctk.CTkCheckBox(
            btn_row, text="Auto-copy", variable=self._auto_copy_var,
            onvalue="on", offvalue="off"
        ).pack(side="left")
        
        self._status_label = ctk.CTkLabel(result, text="", font=ctk.CTkFont(size=12))
        self._status_label.grid(row=3, column=1, sticky="w", padx=10, pady=(0, 15))

    # ----- actions -----

    def _on_generate(self) -> None:
        raw = HardwareIdentifier.get_raw_fingerprint()
        hwid = HardwareIdentifier.get_machine_id()
        self._raw_label.configure(text=raw, text_color=("gray10", "gray90"))
        self.hwid_var.set(hwid)
        self._status_label.configure(text="")
        if self.app:
            self.app.status("Machine ID generated", "success")
        if self._auto_copy_var.get() == "on":
            self._do_copy()

    def _on_copy(self) -> None:
        hwid = self.hwid_var.get()
        if not hwid:
            CTkMessagebox(title="Warning", message="Generate the HWID first.", icon="warning")
            return
        self._do_copy()

    def _do_copy(self) -> None:
        hwid = self.hwid_var.get()
        self.clipboard_clear()
        self.clipboard_append(hwid)
        self._status_label.configure(
            text="\u2705  Copied to clipboard", text_color=Color.SUCCESS
        )
        if self.app:
            self.app.status("HWID copied to clipboard", "success")

    def get_hwid(self) -> str:
        """Allow other tabs to pull the current HWID value."""
        return self.hwid_var.get()
