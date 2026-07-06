"""Tab 4 — Read-only License Information Viewer."""
import tkinter as tk
from datetime import datetime, timezone
from tkinter import filedialog, messagebox, ttk

from ...core.license_validator import LicenseValidator
from ..theme import Color, Font, Pad


class ViewerTab(ttk.Frame):
    """Load a .lic file + public key and display decoded fields read-only."""

    def __init__(self, parent, app=None):
        super().__init__(parent)
        self.app = app
        self._var_pub_key = tk.StringVar()
        self._var_lic_path = tk.StringVar()
        self._build()

    def _build(self) -> None:
        ttk.Label(
            self, text="License Information Viewer (Read-Only)",
            style="Heading.TLabel",
        ).pack(pady=(Pad.XXL, Pad.SM))

        ttk.Label(
            self,
            text=(
                "Load a .lic file to view decoded license information.\n"
                "Requires the matching public key \u2014 no private key needed."
            ),
            justify="center",
        ).pack(pady=(0, Pad.XL))

        # drag-drop hint area
        self._drop_area = ttk.LabelFrame(
            self, text="Drop Zone", padding=Pad.MD
        )
        self._drop_area.pack(fill="x", padx=Pad.XXL, pady=Pad.SM)
        ttk.Label(
            self._drop_area,
            text="\U0001f4c2  Drag & drop .lic and .pem files here\nor use the Browse buttons below",
            font=Font.SMALL, foreground=Color.DISABLED,
            justify="center",
        ).pack()
        self._drop_area.bind("<Button-1>", lambda e: self._focus_current())

        # public key
        kf = ttk.LabelFrame(self, text="Public Key", padding=Pad.MD)
        kf.pack(fill="x", padx=Pad.XXL, pady=Pad.SM)
        kf.columnconfigure(1, weight=1)
        ttk.Label(kf, text="File:").grid(row=0, column=0, sticky="w")
        ttk.Entry(
            kf, textvariable=self._var_pub_key, state="readonly"
        ).grid(row=0, column=1, sticky="ew", padx=Pad.MD)
        ttk.Button(kf, text="Browse\u2026",
                   command=self._browse_pub).grid(row=0, column=2)

        # license file
        lf = ttk.LabelFrame(self, text="License File (.lic)", padding=Pad.MD)
        lf.pack(fill="x", padx=Pad.XXL, pady=Pad.SM)
        lf.columnconfigure(1, weight=1)
        ttk.Label(lf, text="File:").grid(row=0, column=0, sticky="w")
        ttk.Entry(
            lf, textvariable=self._var_lic_path, state="readonly"
        ).grid(row=0, column=1, sticky="ew", padx=Pad.MD)
        ttk.Button(lf, text="Browse\u2026",
                   command=self._browse_lic).grid(row=0, column=2)

        ttk.Button(
            self, text="\U0001f50d  Decode & View",
            command=self._on_decode
        ).pack(pady=Pad.LG)

        # result treeview
        rf = ttk.LabelFrame(
            self, text="Decoded License Information", padding=Pad.LG
        )
        rf.pack(fill="both", expand=True, padx=Pad.XXL, pady=Pad.SM)
        rf.columnconfigure(0, weight=1)
        rf.rowconfigure(0, weight=1)

        columns = ("field", "value")
        self._tree = ttk.Treeview(
            rf, columns=columns, show="headings",
            height=14, selectmode="none",
        )
        self._tree.heading("field", text="Field")
        self._tree.heading("value", text="Value")
        self._tree.column("field", width=160, minwidth=120, anchor="w")
        self._tree.column("value", width=500, minwidth=300, anchor="w")
        self._tree.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(rf, orient="vertical",
                               command=self._tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self._tree.configure(yscrollcommand=scroll.set)

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
            if self.app:
                self.app.status("License decoded successfully", "success")
        except Exception as exc:
            messagebox.showerror("Decode Error", str(exc))
            if self.app:
                self.app.status(f"Decode failed: {exc}", "error")

    def _display(self, payload: dict) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)

        now = int(datetime.now(tz=timezone.utc).timestamp())

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

            self._tree.insert("", tk.END, values=(key, display_val))

        # add blank + status row
        self._tree.insert("", tk.END, values=("", ""))
        exp = payload.get("exp", 0)
        if exp and exp >= now:
            self._tree.insert(
                "", tk.END,
                values=("STATUS", "\u2705  VALID"),
                tags=("success",),
            )
        elif exp and exp < now:
            self._tree.insert(
                "", tk.END,
                values=("STATUS", "\u26d4  EXPIRED"),
                tags=("error",),
            )
        else:
            self._tree.insert(
                "", tk.END,
                values=("STATUS", "\u26a0  NO EXPIRATION SET"),
                tags=("warning",),
            )

        self._tree.tag_configure("success", foreground=Color.SUCCESS)
        self._tree.tag_configure("error", foreground=Color.ERROR)
        self._tree.tag_configure("warning", foreground=Color.WARNING)

    def _focus_current(self) -> None:
        """Placeholder for drag-drop future extension."""
        pass
