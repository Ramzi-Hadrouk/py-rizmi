"""Tab 4 — Read-only License Information Viewer."""
import customtkinter as ctk
import tkinter as tk
from datetime import datetime, timezone
from tkinter import filedialog
from CTkMessagebox import CTkMessagebox

from ...core.license_validator import LicenseValidator
from ..theme import Color


class ViewerTab(ctk.CTkFrame):
    """Load a .lic file + public key and display decoded fields read-only."""

    def __init__(self, parent, app=None):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._var_pub_key = ctk.StringVar()
        self._var_lic_path = ctk.StringVar()
        
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header, text="License Information Viewer",
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=(0, 5))

        ctk.CTkLabel(
            header,
            text=(
                "Load a .lic file to view decoded license information.\n"
                "Requires the matching public key \u2014 no private key needed."
            ),
            justify="center", text_color="gray50"
        ).pack()

        # Input Frame
        input_f = ctk.CTkFrame(self, fg_color=("gray95", "gray13"), corner_radius=8)
        input_f.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        input_f.columnconfigure(1, weight=1)

        # public key
        ctk.CTkLabel(input_f, text="Public Key:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=20, pady=15)
        ctk.CTkEntry(
            input_f, textvariable=self._var_pub_key, state="readonly"
        ).grid(row=0, column=1, sticky="ew", padx=10, pady=15)
        
        btn_pub = ctk.CTkFrame(input_f, fg_color="transparent")
        btn_pub.grid(row=0, column=2, padx=(0, 20), pady=15)
        ctk.CTkButton(btn_pub, text="Browse\u2026", width=80, command=self._browse_pub).pack(side="left")

        # license file
        ctk.CTkLabel(input_f, text="License File (.lic):", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 15))
        ctk.CTkEntry(
            input_f, textvariable=self._var_lic_path, state="readonly"
        ).grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 15))
        
        btn_lic = ctk.CTkFrame(input_f, fg_color="transparent")
        btn_lic.grid(row=1, column=2, padx=(0, 20), pady=(0, 15))
        ctk.CTkButton(btn_lic, text="Browse\u2026", width=80, command=self._browse_lic).pack(side="left")

        ctk.CTkButton(
            input_f, text="\U0001f50d  Decode & View", height=40,
            command=self._on_decode
        ).grid(row=2, column=0, columnspan=3, pady=(10, 20))

        # Result Scrollable Frame (replaces Treeview)
        self._result_f = ctk.CTkScrollableFrame(self, fg_color=("gray95", "gray13"), corner_radius=8)
        self._result_f.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        self._result_f.columnconfigure(1, weight=1)

        self._row_widgets = []

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
            CTkMessagebox(title="Warning", message="Select both a public key and a .lic file.", icon="warning")
            return
        try:
            validator = LicenseValidator.from_file(pub)
            with open(lic, "r") as f:
                token = f.read().strip()
            payload = validator.decode_token(token)
            self._display(payload)
            if self.app:
                self.app.status("License decoded successfully", "success")
        except Exception as exc:
            CTkMessagebox(title="Decode Error", message=str(exc), icon="cancel")
            if self.app:
                self.app.status(f"Decode failed: {exc}", "error")

    def _display(self, payload: dict) -> None:
        for w in self._row_widgets:
            w.destroy()
        self._row_widgets.clear()

        now = int(datetime.now(tz=timezone.utc).timestamp())

        # Headers
        header_f = ctk.CTkLabel(self._result_f, text="Field", font=ctk.CTkFont(weight="bold"))
        header_f.grid(row=0, column=0, sticky="w", padx=20, pady=10)
        header_v = ctk.CTkLabel(self._result_f, text="Value", font=ctk.CTkFont(weight="bold"))
        header_v.grid(row=0, column=1, sticky="w", padx=10, pady=10)
        self._row_widgets.extend([header_f, header_v])

        # Separator
        sep = ctk.CTkFrame(self._result_f, height=2, fg_color=("gray80", "gray30"))
        sep.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        self._row_widgets.append(sep)

        r = 2
        for key, val in payload.items():
            display_val = str(val)
            if key in ("iat", "exp") and isinstance(val, (int, float)):
                if val == 0:
                    display_val = "\u2014  (not set)"
                else:
                    dt = datetime.fromtimestamp(val, tz=timezone.utc)
                    dt_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                    display_val = f"{val}  \u2192  {dt_str}"
                    if key == "exp" and val < now:
                        display_val += "  \u26d4  EXPIRED"
                    elif key == "exp":
                        days = (val - now) // 86400
                        display_val += f"  \u2705  ({days} days remaining)"
            elif key == "features" and isinstance(val, list):
                display_val = ", ".join(val) if val else "\u2014"

            lf = ctk.CTkLabel(self._result_f, text=key, font=ctk.CTkFont(family="Courier", size=13))
            lf.grid(row=r, column=0, sticky="w", padx=20, pady=5)
            lv = ctk.CTkLabel(self._result_f, text=display_val, font=ctk.CTkFont(family="Courier", size=13), justify="left", wraplength=500)
            lv.grid(row=r, column=1, sticky="w", padx=10, pady=5)
            
            self._row_widgets.extend([lf, lv])
            r += 1

        # add blank + status row
        sep2 = ctk.CTkFrame(self._result_f, height=2, fg_color=("gray80", "gray30"))
        sep2.grid(row=r, column=0, columnspan=2, sticky="ew", padx=10, pady=(15, 10))
        self._row_widgets.append(sep2)
        r += 1

        exp = payload.get("exp", 0)
        status_l = ctk.CTkLabel(self._result_f, text="STATUS", font=ctk.CTkFont(weight="bold"))
        status_l.grid(row=r, column=0, sticky="w", padx=20, pady=10)
        
        status_color = Color.FG
        if exp and exp >= now:
            status_text = "\u2705  VALID"
            status_color = Color.SUCCESS
        elif exp and exp < now:
            status_text = "\u26d4  EXPIRED"
            status_color = Color.ERROR
        else:
            status_text = "\u26a0  NO EXPIRATION SET"
            status_color = Color.WARNING

        status_v = ctk.CTkLabel(self._result_f, text=status_text, text_color=status_color, font=ctk.CTkFont(weight="bold"))
        status_v.grid(row=r, column=1, sticky="w", padx=10, pady=10)
        
        self._row_widgets.extend([status_l, status_v])
