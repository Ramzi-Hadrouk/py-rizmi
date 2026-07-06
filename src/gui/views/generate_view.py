"""Tab 3 — License Generation with fully dynamic payload fields."""
import json
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from CTkMessagebox import CTkMessagebox
from datetime import datetime, timezone
from tkcalendar import DateEntry

from ...core.license_issuer import LicenseIssuer
from ...core.license_token import LicensePayload
from ..widgets.dynamic_list import DynamicListWidget
from ..widgets.step_card import StepCard
from ..theme import Color


class GenerateTab(ctk.CTkScrollableFrame):
    """Single-column step-by-step license generation form."""

    def __init__(self, parent, get_hwid_cb=None, app=None):
        super().__init__(parent, fg_color="transparent")
        self._get_hwid_cb = get_hwid_cb
        self.app = app

        # ── input variables ────────────────────────────────────────────
        self._var_client = ctk.StringVar()
        self._var_license_id = ctk.StringVar()
        self._var_hwid = ctk.StringVar()
        self._var_max_clients = ctk.IntVar(value=10)
        self._var_mode = ctk.StringVar(value="offline")
        self._var_server_url = ctk.StringVar()
        self._var_grace_days = ctk.IntVar(value=14)
        self._var_iat_auto = ctk.StringVar(value="on")
        self._var_exp_auto = ctk.StringVar(value="on")
        self._var_exp_days = ctk.IntVar(value=365)
        self._var_private_key_path = ctk.StringVar()

        self._features_widget: DynamicListWidget | None = None
        self._required_entries: list[tuple[ctk.CTkEntry, ctk.StringVar, str]] = []

        self.grid_columnconfigure(0, weight=1)
        self._build()

    # ===================== BUILD =====================

    def _build(self) -> None:
        self._build_step1_key()
        self._build_step2_identity()
        self._build_step3_config()
        self._build_step4_validity()
        self._build_actions()

    # ─── STEP 1: Signing Key ──────────────────────────────────────────

    def _build_step1_key(self) -> None:
        card = StepCard(self, step=1, title="Signing Key  (Private Key)")
        card.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 8))
        b = card.body
        b.columnconfigure(1, weight=1)

        ctk.CTkLabel(b, text="Private Key File:",
                     font=ctk.CTkFont(weight="bold"),
                     text_color="gray50").grid(row=0, column=0, sticky="w", pady=(0, 6))

        self._key_entry = ctk.CTkEntry(
            b, textvariable=self._var_private_key_path,
            state="readonly", placeholder_text="No key selected…"
        )
        self._key_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=(0, 6))

        ctk.CTkButton(b, text="Browse…", width=80,
                      command=self._browse_private_key).grid(
            row=0, column=2, padx=(8, 0), pady=(0, 6))

        ctk.CTkLabel(
            b,
            text="ℹ  Use the Key Management tab to generate and save a private key first.",
            text_color="gray50", font=ctk.CTkFont(size=11),
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 0))

    # ─── STEP 2: License Identity ─────────────────────────────────────

    def _build_step2_identity(self) -> None:
        card = StepCard(self, step=2, title="License Identity")
        card.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))
        b = card.body
        b.columnconfigure(1, weight=1)

        legend = ctk.CTkLabel(
            b, text="* Required fields",
            text_color=Color.ERROR, font=ctk.CTkFont(size=11),
        )
        legend.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        fields = [
            ("Client Name", self._var_client, True, None),
            ("License ID", self._var_license_id, True, None),
            ("Machine HWID", self._var_hwid, True, "hwid"),
        ]

        for i, (label, var, required, kind) in enumerate(fields):
            r = i + 1
            # Label with optional asterisk
            lf = ctk.CTkFrame(b, fg_color="transparent")
            lf.grid(row=r, column=0, sticky="w", padx=(0, 10), pady=8)
            ctk.CTkLabel(lf, text=label,
                         font=ctk.CTkFont(weight="bold")).pack(side="left")
            if required:
                ctk.CTkLabel(lf, text=" *", text_color=Color.ERROR,
                             font=ctk.CTkFont(weight="bold")).pack(side="left")

            entry = ctk.CTkEntry(
                b, textvariable=var,
                placeholder_text=f"Enter {label.lower()}…"
            )
            entry.grid(row=r, column=1, sticky="ew", pady=8)

            if required:
                self._required_entries.append((entry, var, label))

            if kind == "hwid":
                hwid_btns = ctk.CTkFrame(b, fg_color="transparent")
                hwid_btns.grid(row=r, column=2, padx=(8, 0), pady=8)
                ctk.CTkButton(
                    hwid_btns, text="← Tab 1", width=75, height=30,
                    command=self._pull_hwid,
                ).pack(side="left")
                ctk.CTkButton(
                    hwid_btns, text="Paste", width=65, height=30,
                    fg_color="gray50", hover_color="gray40",
                    command=self._paste_hwid,
                ).pack(side="left", padx=(6, 0))

    # ─── STEP 3: Configuration ────────────────────────────────────────

    def _build_step3_config(self) -> None:
        card = StepCard(self, step=3, title="Configuration")
        card.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 8))
        b = card.body
        b.columnconfigure(0, weight=1)

        # ── 3-column mini row for compact settings ─────────────────────
        mini = ctk.CTkFrame(b, fg_color="transparent")
        mini.pack(fill="x", pady=(0, 12))
        mini.columnconfigure(0, weight=1)
        mini.columnconfigure(1, weight=1)
        mini.columnconfigure(2, weight=1)

        def _mini_card(parent, col, title, widget_factory):
            mc = ctk.CTkFrame(parent, fg_color=("gray88", "gray17"), corner_radius=8)
            mc.grid(row=0, column=col, sticky="nsew",
                    padx=(0 if col == 0 else 8, 0))
            ctk.CTkLabel(mc, text=title,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="gray50").pack(
                anchor="w", padx=12, pady=(10, 4))
            widget_factory(mc).pack(anchor="w", padx=12, pady=(0, 10))

        _mini_card(mini, 0, "Max Clients",
                   lambda p: ctk.CTkEntry(p, textvariable=self._var_max_clients, width=90))
        _mini_card(mini, 1, "Mode",
                   lambda p: ctk.CTkComboBox(p, variable=self._var_mode,
                                              values=["offline", "online"],
                                              state="readonly", width=110))
        _mini_card(mini, 2, "Grace Days",
                   lambda p: ctk.CTkEntry(p, textvariable=self._var_grace_days, width=90))

        # ── Server URL ─────────────────────────────────────────────────
        url_row = ctk.CTkFrame(b, fg_color="transparent")
        url_row.pack(fill="x", pady=(0, 12))
        url_row.columnconfigure(1, weight=1)

        ctk.CTkLabel(url_row, text="Server URL",
                     font=ctk.CTkFont(weight="bold"),
                     text_color="gray50").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ctk.CTkLabel(url_row, text="optional",
                     font=ctk.CTkFont(size=10),
                     text_color="gray60").grid(row=0, column=0, sticky="w", padx=(90, 0))
        ctk.CTkEntry(url_row, textvariable=self._var_server_url,
                     placeholder_text="https://…  (only needed for online mode)").grid(
            row=0, column=1, sticky="ew")

        # ── Features ──────────────────────────────────────────────────
        ctk.CTkLabel(b, text="Features",
                     font=ctk.CTkFont(weight="bold"),
                     text_color="gray50").pack(anchor="w", pady=(0, 6))

        self._features_widget = DynamicListWidget(b, label="Feature")
        self._features_widget.pack(fill="x")

    # ─── STEP 4: Validity Dates ───────────────────────────────────────

    def _build_step4_validity(self) -> None:
        card = StepCard(self, step=4, title="Validity Dates")
        card.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 8))
        b = card.body
        b.columnconfigure(0, weight=1)

        # helper to build one date row
        def date_row(parent, row, label, var_auto, toggle_cmd, entry_attr, days_var=None):
            f = ctk.CTkFrame(parent, fg_color=("gray88", "gray17"), corner_radius=8)
            f.grid(row=row, column=0, sticky="ew", pady=(0, 8))

            hdr = ctk.CTkFrame(f, fg_color="transparent")
            hdr.pack(fill="x", padx=14, pady=(10, 6))
            ctk.CTkLabel(hdr, text=label,
                         font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")

            body = ctk.CTkFrame(f, fg_color="transparent")
            body.pack(fill="x", padx=14, pady=(0, 10))

            chk = ctk.CTkCheckBox(
                body, text="Auto", variable=var_auto,
                onvalue="on", offvalue="off", command=toggle_cmd,
            )
            chk.pack(side="left")

            if days_var is not None:
                ctk.CTkLabel(body, text="days:", text_color="gray50").pack(
                    side="left", padx=(16, 6))
                ctk.CTkEntry(body, textvariable=days_var, width=60).pack(side="left")
                ctk.CTkLabel(body, text="  or pick a date:",
                             text_color="gray50").pack(side="left", padx=(16, 6))
            else:
                ctk.CTkLabel(body, text="  or pick a date:",
                             text_color="gray50").pack(side="left", padx=(16, 6))

            picker = DateEntry(
                body, width=14, date_pattern="y-mm-dd",
                background="gray20", foreground="white", borderwidth=1,
                state="disabled",
            )
            picker.pack(side="left")
            setattr(self, entry_attr, picker)

        b.columnconfigure(0, weight=1)
        date_row(b, 0, "Issued At (iat)",
                 self._var_iat_auto, self._toggle_iat,
                 "_iat_manual_entry")
        date_row(b, 1, "Expires At (exp)",
                 self._var_exp_auto, self._toggle_exp,
                 "_exp_manual_entry", days_var=self._var_exp_days)

    # ─── Action bar ───────────────────────────────────────────────────

    def _build_actions(self) -> None:
        af = ctk.CTkFrame(self, fg_color="transparent")
        af.grid(row=4, column=0, sticky="ew", padx=20, pady=(4, 28))
        af.columnconfigure(0, weight=1)

        # Primary CTA — full width
        ctk.CTkButton(
            af,
            text="🔐  Generate License",
            command=self._on_generate,
            height=48, font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=Color.ACCENT, hover_color=Color.ACCENT_HOVER,
            corner_radius=8,
        ).grid(row=0, column=0, sticky="ew", pady=(0, 10))

        # Secondary actions row
        sec = ctk.CTkFrame(af, fg_color="transparent")
        sec.grid(row=1, column=0, sticky="w")

        ctk.CTkButton(
            sec, text="👁  Preview Payload (JSON)",
            command=self._on_preview,
            height=34, fg_color=Color.WARNING, hover_color=Color.WARNING_HOVER,
        ).pack(side="left")
        ctk.CTkButton(
            sec, text="🗑  Clear Form",
            command=self._on_clear,
            height=34, fg_color="gray50", hover_color="gray40",
        ).pack(side="left", padx=(10, 0))

    # ===================== TOGGLES =====================

    def _toggle_iat(self) -> None:
        s = "disabled" if self._var_iat_auto.get() == "on" else "normal"
        self._iat_manual_entry.configure(state=s)

    def _toggle_exp(self) -> None:
        s = "disabled" if self._var_exp_auto.get() == "on" else "normal"
        self._exp_manual_entry.configure(state=s)

    # ===================== HELPERS =====================

    def _highlight(self, entry: ctk.CTkEntry, valid: bool) -> None:
        color = ["#979DA2", "#565B5E"] if valid else Color.ERROR
        entry.configure(border_color=color)

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
        CTkMessagebox(title="Warning",
                      message="No HWID found. Generate it in Tab 1 first.",
                      icon="warning")

    def _paste_hwid(self) -> None:
        try:
            clip = self.clipboard_get()
            self._var_hwid.set(clip.strip())
        except tk.TclError:
            CTkMessagebox(title="Warning", message="Clipboard is empty.", icon="warning")

    def _validate_required(self) -> list[str]:
        missing = []
        for entry, var, label in self._required_entries:
            if not var.get().strip():
                self._highlight(entry, False)
                missing.append(label)
            else:
                self._highlight(entry, True)
        return missing

    # ===================== PAYLOAD =====================

    def _build_payload(self) -> LicensePayload | None:
        missing = self._validate_required()
        if missing:
            msg = "Please fill in required fields: " + ", ".join(missing)
            CTkMessagebox(title="Validation Error", message=msg, icon="cancel")
            if self.app:
                self.app.status(f"Validation failed: {', '.join(missing)}", "error")
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

        if self._var_iat_auto.get() == "on":
            payload.set_auto_iat()
        else:
            try:
                d = self._iat_manual_entry.get_date()
                dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
                payload.iat = int(dt.timestamp())
            except Exception as e:
                CTkMessagebox(title="Invalid Date",
                              message=f"Issued At date error: {e}", icon="cancel")
                return None

        if self._var_exp_auto.get() == "on":
            payload.set_auto_exp(self._var_exp_days.get())
        else:
            try:
                d = self._exp_manual_entry.get_date()
                dt = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)
                payload.exp = int(dt.timestamp())
            except Exception as e:
                CTkMessagebox(title="Invalid Date",
                              message=f"Expiration date error: {e}", icon="cancel")
                return None

        return payload

    # ===================== ACTIONS =====================

    def _on_clear(self) -> None:
        self._var_client.set("")
        self._var_license_id.set("")
        self._var_hwid.set("")
        self._var_max_clients.set(10)
        self._var_mode.set("offline")
        self._var_server_url.set("")
        self._var_grace_days.set(14)
        self._var_iat_auto.set("on")
        self._var_exp_auto.set("on")
        self._var_exp_days.set(365)
        today = datetime.now().date()
        self._iat_manual_entry.set_date(today)
        self._exp_manual_entry.set_date(today)
        self._features_widget.clear()
        for entry, _, _ in self._required_entries:
            self._highlight(entry, True)
        self._toggle_iat()
        self._toggle_exp()
        if self.app:
            self.app.status("Form cleared", "info")

    def _on_preview(self) -> None:
        payload = self._build_payload()
        if payload is None:
            return
        win = ctk.CTkToplevel(self)
        win.title("Payload Preview — JSON")
        win.geometry("520x480")
        win.grab_set()
        text = ctk.CTkTextbox(win, wrap="none",
                               font=ctk.CTkFont(family="Courier", size=13))
        text.pack(fill="both", expand=True, padx=16, pady=16)
        text.insert("1.0", json.dumps(payload.to_dict(), indent=2))
        text.configure(state="disabled")

    def _on_generate(self) -> None:
        payload = self._build_payload()
        if payload is None:
            return

        key_path = self._var_private_key_path.get()
        if not key_path:
            CTkMessagebox(title="No Key Selected",
                          message="Please select a private key file in Step 1.",
                          icon="cancel")
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
            CTkMessagebox(title="License Issued ✅",
                          message=f"License written to:\n{save_path}", icon="check")
            if self.app:
                self.app.status(f"License issued for {payload.client} — {save_path}", "success")
        except Exception as exc:
            CTkMessagebox(title="Error", message=f"Failed to generate license:\n{exc}",
                          icon="cancel")
            if self.app:
                self.app.status(f"License generation failed: {exc}", "error")
