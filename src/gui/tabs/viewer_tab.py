"""Tab 3 — Read-only License Information Viewer (recommendation)."""
import tkinter as tk
from datetime import datetime, timezone
from tkinter import filedialog, messagebox, ttk

from ...core.license_validator import LicenseValidator


class ViewerTab(ttk.Frame):
    """Load a .lic file + public key and display decoded fields read-only."""

    def __init__(self, parent):
        super().__init__(parent)
        self._var_pub_key = tk.StringVar()
        self._var_lic_path = tk.StringVar()
        self._build()

    def _build(self) -> None:
        ttk.Label(
            self, text="License Information Viewer (Read-Only)",
            font=("TkDefaultFont", 14, "bold"),
        ).pack(pady=(24, 4))

        ttk.Label(
            self,
            text=(
                "Load a .lic file to view decoded license information.\n"
                "Requires the matching public key — no private key needed."
            ),
            justify="center",
        ).pack(pady=(0, 16))

        # public key
        kf = ttk.LabelFrame(self, text="Public Key", padding=10)
        kf.pack(fill="x", padx=24, pady=4)
        ttk.Label(kf, text="File:").grid(row=0, column=0, sticky="w")
        ttk.Entry(kf, textvariable=self._var_pub_key,
                  width=48, state="readonly").grid(row=0, column=1, padx=8)
        ttk.Button(kf, text="Browse\u2026",
                   command=self._browse_pub).grid(row=0, column=2)

        # license file
        lf = ttk.LabelFrame(self, text="License File (.lic)", padding=10)
        lf.pack(fill="x", padx=24, pady=4)
        ttk.Label(lf, text="File:").grid(row=0, column=0, sticky="w")
        ttk.Entry(lf, textvariable=self._var_lic_path,
                  width=48, state="readonly").grid(row=0, column=1, padx=8)
        ttk.Button(lf, text="Browse\u2026",
                   command=self._browse_lic).grid(row=0, column=2)

        ttk.Button(self, text="\U0001f50d  Decode & View",
                   command=self._on_decode).pack(pady=12)

        # result
        rf = ttk.LabelFrame(self, text="Decoded License Information", padding=12)
        rf.pack(fill="both", expand=True, padx=24, pady=4)

        self._text = tk.Text(rf, height=18, state="disabled",
                             wrap="word", font=("Consolas", 11))
        self._text.pack(fill="both", expand=True)

    # ----- file browsers -----

    def _browse_pub(self) -> None:
        p = filedialog.askopenfilename(
            title="Select Public Key",
            filetypes=[("PEM files", "*.pem"), ("All files", "*.*")],
        )
        if p:
            self._var_pub_key.set(p)

    def _browse_lic(self) -> None:
        p = filedialog.askopenfilename(
            title="Select License File",
            filetypes=[("License files", "*.lic"), ("All files", "*.*")],
        )
        if p:
            self._var_lic_path.set(p)

    # ----- decode -----

    def _on_decode(self) -> None:
        pub = self._var_pub_key.get()
        lic = self._var_lic_path.get()
        if not pub or not lic:
            messagebox.showwarning("Warning",
                                   "Select both a public key and a .lic file.")
            return
        try:
            validator = LicenseValidator.from_file(pub)
            with open(lic, "r") as f:
                token = f.read().strip()
            payload = validator.decode_token(token)
            self._display(payload)
        except Exception as exc:
            messagebox.showerror("Decode Error", str(exc))

    def _display(self, payload: dict) -> None:
        self._text.config(state="normal")
        self._text.delete("1.0", tk.END)

        lines: list[str] = []
        lines.append(f"{'FIELD':<18} VALUE")
        lines.append("=" * 70)

        for key, val in payload.items():
            if key in ("iat", "exp") and isinstance(val, (int, float)):
                dt = datetime.fromtimestamp(val, tz=timezone.utc)
                dt_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                lines.append(f"{key:<18} {val}  \u2192  {dt_str}")
            elif key == "features" and isinstance(val, list):
                lines.append(f"{key:<18} {', '.join(val) if val else '\u2014'}")
            else:
                lines.append(f"{key:<18} {val}")

        # status
        lines.append("")
        lines.append("-" * 70)
        exp = payload.get("exp", 0)
        if exp:
            now = int(datetime.now(tz=timezone.utc).timestamp())
            if now > exp:
                lines.append("STATUS: \u26d4 EXPIRED")
            else:
                days_left = (exp - now) // 86_400
                lines.append(f"STATUS: \u2705 VALID  ({days_left} days remaining)")
        else:
            lines.append("STATUS: \u26a0 NO EXPIRATION SET")

        self._text.insert("1.0", "\n".join(lines))
        self._text.config(state="disabled")
