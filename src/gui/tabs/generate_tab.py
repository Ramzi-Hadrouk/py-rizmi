"""Tab 3 — License Generation with fully dynamic payload fields (Task 4.4)."""
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime, timezone

from ...core.keypair import KeyPairManager
from ...core.license_issuer import LicenseIssuer
from ...core.license_token import LicensePayload
from ..widgets.dynamic_list import DynamicListWidget
from ..theme import Color, Font, Pad


class GenerateTab(ttk.Frame):
    """Every payload field is a bound input widget — zero hard-coded values."""

    def __init__(self, parent, get_hwid_cb=None, app=None):
        super().__init__(parent)
        self._get_hwid_cb = get_hwid_cb
        self.app = app

        # --- input variables ---
        self._var_client = tk.StringVar()
        self._var_license_id = tk.StringVar()
        self._var_hwid = tk.StringVar()
        self._var_max_clients = tk.IntVar(value=10)
        self._var_mode = tk.StringVar(value="offline")
        self._var_server_url = tk.StringVar()
        self._var_grace_days = tk.IntVar(value=14)

        self._var_iat_auto = tk.BooleanVar(value=True)
        self._var_exp_auto = tk.BooleanVar(value=True)
        self._var_exp_days = tk.IntVar(value=365)
        self._var_iat_manual = tk.StringVar()
        self._var_exp_manual = tk.StringVar()

        self._var_private_key_path = tk.StringVar()

        self._features_widget: DynamicListWidget | None = None

        # --- inline validation tracking ---
        self._required_entries: list[tuple[ttk.Entry, tk.StringVar, str]] = []

        self._build()

    # ===================== UI =====================

    def _build(self) -> None:
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)

        inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._build_key_section(inner)
        self._build_payload_section(inner)
        self._build_action_section(inner)

    # ---------- key section ----------

    def _build_key_section(self, parent) -> None:
        f = ttk.LabelFrame(
            parent, text="\u2460  Signing Key (Private Key)", padding=Pad.LG
        )
        f.pack(fill="x", padx=Pad.XL, pady=(Pad.XL, Pad.SM))
        f.columnconfigure(1, weight=1)

        ttk.Label(f, text="Private Key File:").grid(
            row=0, column=0, sticky="w", pady=Pad.SM
        )
        self._key_entry = ttk.Entry(
            f, textvariable=self._var_private_key_path, state="readonly"
        )
        self._key_entry.grid(row=0, column=1, sticky="ew", padx=Pad.MD, pady=Pad.SM)
        ttk.Button(
            f, text="Browse\u2026", command=self._browse_private_key
        ).grid(row=0, column=2, pady=Pad.SM)

        ttk.Label(
            f,
            text=(
                "Tip: Use Tab 2 (Key Management) to generate and validate keys"
            ),
            font=Font.SMALL, foreground=Color.DISABLED,
        ).grid(row=1, column=1, sticky="w", padx=Pad.MD)

    # ---------- payload section ----------

    def _build_payload_section(self, parent) -> None:
        f = ttk.LabelFrame(
            parent, text="\u2461  License Payload", padding=Pad.LG
        )
        f.pack(fill="x", padx=Pad.XL, pady=Pad.SM)
        f.columnconfigure(1, weight=1)

        r = 0
        fields = [
            ("Client / Deployment:", self._var_client, True),
            ("License ID:", self._var_license_id, True),
            ("HWID:", self._var_hwid, True),
        ]
        for label, var, required in fields:
            ttk.Label(f, text=label).grid(
                row=r, column=0, sticky="w", pady=Pad.SM
            )
            entry = ttk.Entry(f, textvariable=var)
            entry.grid(row=r, column=1, sticky="ew", padx=Pad.MD, pady=Pad.SM)
            if required:
                self._required_entries.append((entry, var, label.rstrip(":")))
            # HWID gets helper buttons
            if label == "HWID:":
                btn_row = ttk.Frame(f)
                btn_row.grid(row=r, column=2, sticky="w", padx=(0, Pad.MD))
                ttk.Button(
                    btn_row, text="From Tab 1", width=10,
                    command=self._pull_hwid
                ).pack(side="left", padx=(Pad.SM, Pad.SM))
                ttk.Button(
                    btn_row, text="Paste", width=6,
                    command=self._paste_hwid
                ).pack(side="left")
            r += 1

        # features
        ttk.Label(f, text="Features:").grid(
            row=r, column=0, sticky="nw", pady=Pad.SM
        )
        feat_container = ttk.Frame(f)
        feat_container.grid(
            row=r, column=1, columnspan=2, sticky="ew", padx=Pad.MD, pady=Pad.SM
        )
        self._features_widget = DynamicListWidget(feat_container, label="Feature")
        self._features_widget.pack(fill="x")
        r += 1

        # max_clients
        ttk.Label(f, text="Max Clients:").grid(
            row=r, column=0, sticky="w", pady=Pad.SM
        )
        ttk.Spinbox(f, from_=1, to=99999, textvariable=self._var_max_clients,
                    width=10).grid(row=r, column=1, sticky="w", padx=Pad.MD, pady=Pad.SM)
        r += 1

        # mode
        ttk.Label(f, text="Mode:").grid(
            row=r, column=0, sticky="w", pady=Pad.SM
        )
        ttk.Combobox(f, textvariable=self._var_mode, values=["offline", "online"],
                     state="readonly", width=12).grid(row=r, column=1, sticky="w", padx=Pad.MD, pady=Pad.SM)
        r += 1

        # server_url
        ttk.Label(f, text="Server URL:").grid(
            row=r, column=0, sticky="w", pady=Pad.SM
        )
        ttk.Entry(f, textvariable=self._var_server_url).grid(
            row=r, column=1, sticky="ew", padx=Pad.MD, pady=Pad.SM
        )
        r += 1

        # grace_days
        ttk.Label(f, text="Grace Days:").grid(
            row=r, column=0, sticky="w", pady=Pad.SM
        )
        ttk.Spinbox(f, from_=0, to=365, textvariable=self._var_grace_days,
                    width=10).grid(row=r, column=1, sticky="w", padx=Pad.MD, pady=Pad.SM)
        r += 1

        # iat
        ttk.Label(f, text="Issued At (iat):").grid(
            row=r, column=0, sticky="w", pady=Pad.SM
        )
        iat_row = ttk.Frame(f)
        iat_row.grid(row=r, column=1, sticky="w", padx=Pad.MD, pady=Pad.SM)
        ttk.Checkbutton(iat_row, text="Auto (now)", variable=self._var_iat_auto,
                        command=self._toggle_iat).pack(side="left")
        self._iat_manual_entry = ttk.Entry(iat_row, textvariable=self._var_iat_manual,
                                           width=25, state="disabled")
        self._iat_manual_entry.pack(side="left", padx=Pad.MD)
        r += 1

        # exp
        ttk.Label(f, text="Expiration (exp):").grid(
            row=r, column=0, sticky="w", pady=Pad.SM
        )
        exp_row = ttk.Frame(f)
        exp_row.grid(row=r, column=1, sticky="w", padx=Pad.MD, pady=Pad.SM)
        ttk.Checkbutton(exp_row, text="Auto", variable=self._var_exp_auto,
                        command=self._toggle_exp).pack(side="left")
        ttk.Label(exp_row, text="days:").pack(side="left", padx=(Pad.MD, Pad.XS))
        ttk.Spinbox(exp_row, from_=1, to=3650, textvariable=self._var_exp_days,
                    width=8).pack(side="left")
        ttk.Label(exp_row, text="or manual:").pack(side="left", padx=(Pad.LG, Pad.XS))
        self._exp_manual_entry = ttk.Entry(exp_row, textvariable=self._var_exp_manual,
                                           width=25, state="disabled")
        self._exp_manual_entry.pack(side="left")
        r += 1

    # ---------- actions ----------

    def _build_action_section(self, parent) -> None:
        f = ttk.Frame(parent)
        f.pack(fill="x", padx=Pad.XL, pady=Pad.XL)
        ttk.Button(
            f, text="\U0001f510  Generate License",
            command=self._on_generate
        ).pack(side="left", padx=(0, Pad.MD))
        ttk.Button(
            f, text="\U0001f4cb  Preview Payload (JSON)",
            command=self._on_preview
        ).pack(side="left", padx=(0, Pad.MD))
        ttk.Button(
            f, text="\U0001f5d1  Clear Form",
            command=self._on_clear
        ).pack(side="left")

    # ===================== toggles =====================

    def _toggle_iat(self) -> None:
        self._iat_manual_entry.config(
            state="disabled" if self._var_iat_auto.get() else "normal"
        )

    def _toggle_exp(self) -> None:
        self._exp_manual_entry.config(
            state="disabled" if self._var_exp_auto.get() else "normal"
        )

    # ===================== helpers =====================

    def _highlight(self, entry: ttk.Entry, valid: bool) -> None:
        """Set entry border color to indicate validation state."""
        bg = Color.WHITE if valid else Color.ERROR_LIGHT
        entry.config(style="TEntry")
        entry.configure(background=bg)

    def _browse_private_key(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Private Key",
            filetypes=[("PEM files", "*.pem"), ("All files", "*.*")],
        )
        if path:
            self._var_private_key_path.set(path)

    def _pull_hwid(self) -> None:
        if self._get_hwid_cb:
            hwid = self._get_hwid_cb()
            if hwid:
                self._var_hwid.set(hwid)
                return
        messagebox.showwarning("Warning",
                               "No HWID found. Generate it in Tab 1 first.")

    def _paste_hwid(self) -> None:
        try:
            clip = self.clipboard_get()
            self._var_hwid.set(clip.strip())
        except tk.TclError:
            messagebox.showwarning("Warning", "Clipboard is empty.")

    def _validate_required(self) -> list[str]:
        """Return list of missing field names. Highlights invalid fields."""
        missing = []
        for entry, var, label in self._required_entries:
            if not var.get().strip():
                self._highlight(entry, False)
                missing.append(label)
            else:
                self._highlight(entry, True)
        return missing

    # ===================== payload building =====================

    def _build_payload(self) -> LicensePayload | None:
        missing = self._validate_required()
        if missing:
            msg = "Required fields: " + ", ".join(missing)
            messagebox.showerror("Validation", msg)
            if self.app:
                self.app.status(f"Validation failed: {msg}", "error")
            return None

        payload = LicensePayload(
            client=self._var_client.get().strip(),
            license_id=self._var_license_id.get().strip(),
            hwid=self._var_hwid.get().strip(),
            features=self._features_widget.get_values(),
            max_clients=self._var_max_clients.get(),
            mode=self._var_mode.get(),
            server_url=self._var_server_url.get().strip(),
            grace_days=self._var_grace_days.get(),
        )

        if self._var_iat_auto.get():
            payload.set_auto_iat()
        else:
            iat_str = self._var_iat_manual.get().strip()
            try:
                payload.iat = self._parse_timestamp(iat_str)
            except ValueError:
                messagebox.showerror(
                    "Validation",
                    f"Invalid IAT format: {iat_str}\nUse epoch seconds or ISO 8601.",
                )
                return None

        if self._var_exp_auto.get():
            payload.set_auto_exp(self._var_exp_days.get())
        else:
            exp_str = self._var_exp_manual.get().strip()
            try:
                payload.exp = self._parse_timestamp(exp_str)
            except ValueError:
                messagebox.showerror(
                    "Validation",
                    f"Invalid EXP format: {exp_str}\nUse epoch seconds or ISO 8601.",
                )
                return None

        return payload

    @staticmethod
    def _parse_timestamp(s: str) -> int:
        s = s.strip()
        if s.isdigit():
            return int(s)
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())

    # ===================== actions =====================

    def _on_clear(self) -> None:
        self._var_client.set("")
        self._var_license_id.set("")
        self._var_hwid.set("")
        self._var_max_clients.set(10)
        self._var_mode.set("offline")
        self._var_server_url.set("")
        self._var_grace_days.set(14)
        self._var_iat_auto.set(True)
        self._var_exp_auto.set(True)
        self._var_exp_days.set(365)
        self._var_iat_manual.set("")
        self._var_exp_manual.set("")
        self._features_widget.clear()
        for entry, _, _ in self._required_entries:
            self._highlight(entry, True)
        if self.app:
            self.app.status("Form cleared", "info")

    def _on_preview(self) -> None:
        payload = self._build_payload()
        if payload is None:
            return
        win = tk.Toplevel(self)
        win.title("Payload Preview (JSON)")
        win.geometry("500x500")
        text = tk.Text(win, wrap="word", font=Font.MONO)
        text.pack(fill="both", expand=True, padx=Pad.MD, pady=Pad.MD)
        pretty = json.dumps(payload.to_dict(), indent=2)
        text.insert("1.0", pretty)
        text.config(state="disabled")

    def _on_generate(self) -> None:
        payload = self._build_payload()
        if payload is None:
            return

        key_path = self._var_private_key_path.get()
        if not key_path:
            messagebox.showerror("Error", "Select or generate a private key first.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Save License File",
            defaultextension=".lic",
            filetypes=[("License files", "*.lic"), ("All files", "*.*")],
        )
        if not save_path:
            return

        try:
            issuer = LicenseIssuer.from_file(key_path)
            issuer.issue_to_file(payload, save_path)
            messagebox.showinfo("Success",
                                f"License written to:\n{save_path}")
            if self.app:
                self.app.status(
                    f"License issued for {payload.client} \u2014 {save_path}",
                    "success",
                )
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to generate license:\n{exc}")
            if self.app:
                self.app.status(f"License generation failed: {exc}", "error")
