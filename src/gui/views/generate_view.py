"""Tab 3 — License Generation with fully dynamic payload fields (Task 4.4)."""
import json
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from CTkMessagebox import CTkMessagebox
from datetime import datetime, timezone
from tkcalendar import DateEntry

from ...core.keypair import KeyPairManager
from ...core.license_issuer import LicenseIssuer
from ...core.license_token import LicensePayload
from ..widgets.dynamic_list import DynamicListWidget
from ..theme import Color


class GenerateTab(ctk.CTkScrollableFrame):
    """Every payload field is a bound input widget — zero hard-coded values."""

    def __init__(self, parent, get_hwid_cb=None, app=None):
        super().__init__(parent, fg_color="transparent")
        self._get_hwid_cb = get_hwid_cb
        self.app = app

        # --- input variables ---
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

        # --- inline validation tracking ---
        self._required_entries: list[tuple[ctk.CTkEntry, ctk.StringVar, str]] = []

        self.grid_columnconfigure(0, weight=1)
        self._build()

    # ===================== UI =====================

    def _build(self) -> None:
        self._build_key_section()
        self._build_payload_section()
        self._build_action_section()

    # ---------- key section ----------

    def _build_key_section(self) -> None:
        f = ctk.CTkFrame(self, fg_color=("gray95", "gray13"), corner_radius=8)
        f.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 10))
        f.columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="\u2460  Signing Key (Private Key)", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(20, 10))

        ctk.CTkLabel(f, text="Private Key File:", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=0, sticky="w", padx=20, pady=10
        )
        self._key_entry = ctk.CTkEntry(
            f, textvariable=self._var_private_key_path, state="readonly"
        )
        self._key_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=10)
        
        btn_key = ctk.CTkFrame(f, fg_color="transparent")
        btn_key.grid(row=1, column=2, padx=(0, 20), pady=10)
        ctk.CTkButton(btn_key, text="Browse\u2026", width=80, command=self._browse_private_key).pack(side="left")

        ctk.CTkLabel(
            f,
            text="Tip: Use Tab 2 (Key Management) to generate and validate keys",
            text_color="gray50", font=ctk.CTkFont(size=12)
        ).grid(row=2, column=1, sticky="w", padx=10, pady=(0, 20))

    # ---------- payload section ----------

    def _build_payload_section(self) -> None:
        f = ctk.CTkFrame(self, fg_color=("gray95", "gray13"), corner_radius=8)
        f.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        f.columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="\u2461  License Payload", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(20, 10))

        r = 1
        fields = [
            ("Client / Deployment:", self._var_client, True),
            ("License ID:", self._var_license_id, True),
            ("HWID:", self._var_hwid, True),
        ]
        
        for label, var, required in fields:
            ctk.CTkLabel(f, text=label, font=ctk.CTkFont(weight="bold")).grid(
                row=r, column=0, sticky="w", padx=20, pady=10
            )
            entry = ctk.CTkEntry(f, textvariable=var)
            entry.grid(row=r, column=1, sticky="ew", padx=10, pady=10)
            
            if required:
                self._required_entries.append((entry, var, label.rstrip(":")))
                
            # HWID gets helper buttons
            if label == "HWID:":
                btn_row = ctk.CTkFrame(f, fg_color="transparent")
                btn_row.grid(row=r, column=2, sticky="w", padx=(0, 20))
                ctk.CTkButton(btn_row, text="From Tab 1", width=90, command=self._pull_hwid).pack(side="left", padx=(0, 10))
                ctk.CTkButton(btn_row, text="Paste", width=60, fg_color="gray50", hover_color="gray40", command=self._paste_hwid).pack(side="left")
            r += 1

        # features
        ctk.CTkLabel(f, text="Features:", font=ctk.CTkFont(weight="bold")).grid(
            row=r, column=0, sticky="nw", padx=20, pady=(15, 0)
        )
        feat_container = ctk.CTkFrame(f, fg_color="transparent")
        feat_container.grid(
            row=r, column=1, columnspan=2, sticky="ew", padx=10, pady=(15, 0)
        )
        self._features_widget = DynamicListWidget(feat_container, label="Feature")
        self._features_widget.pack(fill="x", pady=(0, 10))
        r += 1

        # max_clients
        ctk.CTkLabel(f, text="Max Clients:", font=ctk.CTkFont(weight="bold")).grid(
            row=r, column=0, sticky="w", padx=20, pady=10
        )
        self._max_clients_entry = ctk.CTkEntry(f, textvariable=self._var_max_clients, width=120)
        self._max_clients_entry.grid(row=r, column=1, sticky="w", padx=10, pady=10)
        r += 1

        # mode
        ctk.CTkLabel(f, text="Mode:", font=ctk.CTkFont(weight="bold")).grid(
            row=r, column=0, sticky="w", padx=20, pady=10
        )
        ctk.CTkComboBox(f, variable=self._var_mode, values=["offline", "online"],
                     state="readonly", width=120).grid(row=r, column=1, sticky="w", padx=10, pady=10)
        r += 1

        # server_url
        ctk.CTkLabel(f, text="Server URL:", font=ctk.CTkFont(weight="bold")).grid(
            row=r, column=0, sticky="w", padx=20, pady=10
        )
        ctk.CTkEntry(f, textvariable=self._var_server_url).grid(
            row=r, column=1, sticky="ew", padx=10, pady=10
        )
        r += 1

        # grace_days
        ctk.CTkLabel(f, text="Grace Days:", font=ctk.CTkFont(weight="bold")).grid(
            row=r, column=0, sticky="w", padx=20, pady=10
        )
        ctk.CTkEntry(f, textvariable=self._var_grace_days, width=120).grid(row=r, column=1, sticky="w", padx=10, pady=10)
        r += 1

        # iat
        ctk.CTkLabel(f, text="Issued At (iat):", font=ctk.CTkFont(weight="bold")).grid(
            row=r, column=0, sticky="w", padx=20, pady=10
        )
        iat_row = ctk.CTkFrame(f, fg_color="transparent")
        iat_row.grid(row=r, column=1, sticky="w", padx=10, pady=10)
        ctk.CTkCheckBox(iat_row, text="Auto (now)", variable=self._var_iat_auto, onvalue="on", offvalue="off",
                        command=self._toggle_iat).pack(side="left")
        self._iat_manual_entry = DateEntry(iat_row, width=15, background='gray20', foreground='white', borderwidth=0, date_pattern='y-mm-dd', state="disabled")
        self._iat_manual_entry.pack(side="left", padx=20)
        r += 1

        # exp
        ctk.CTkLabel(f, text="Expiration (exp):", font=ctk.CTkFont(weight="bold")).grid(
            row=r, column=0, sticky="w", padx=20, pady=(10, 20)
        )
        exp_row = ctk.CTkFrame(f, fg_color="transparent")
        exp_row.grid(row=r, column=1, columnspan=2, sticky="w", padx=10, pady=(10, 20))
        
        ctk.CTkCheckBox(exp_row, text="Auto", variable=self._var_exp_auto, onvalue="on", offvalue="off",
                        command=self._toggle_exp).pack(side="left")
        ctk.CTkLabel(exp_row, text="days:").pack(side="left", padx=(20, 10))
        ctk.CTkEntry(exp_row, textvariable=self._var_exp_days, width=60).pack(side="left")
        
        ctk.CTkLabel(exp_row, text="or manual date:").pack(side="left", padx=(30, 10))
        self._exp_manual_entry = DateEntry(exp_row, width=15, background='gray20', foreground='white', borderwidth=0, date_pattern='y-mm-dd', state="disabled")
        self._exp_manual_entry.pack(side="left")
        r += 1

    # ---------- actions ----------

    def _build_action_section(self) -> None:
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 30))
        
        ctk.CTkButton(
            f, text="\U0001f510  Generate License",
            command=self._on_generate, height=40, font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left", padx=(0, 20))
        
        ctk.CTkButton(
            f, text="\U0001f4cb  Preview Payload (JSON)",
            command=self._on_preview, height=40, fg_color="#d97706", hover_color="#b45309"
        ).pack(side="left", padx=(0, 20))
        
        ctk.CTkButton(
            f, text="\U0001f5d1  Clear Form",
            command=self._on_clear, height=40, fg_color="gray50", hover_color="gray40"
        ).pack(side="left")

    # ===================== toggles =====================

    def _toggle_iat(self) -> None:
        self._iat_manual_entry.configure(
            state="disabled" if self._var_iat_auto.get() == "on" else "normal"
        )

    def _toggle_exp(self) -> None:
        self._exp_manual_entry.configure(
            state="disabled" if self._var_exp_auto.get() == "on" else "normal"
        )

    # ===================== helpers =====================

    def _highlight(self, entry: ctk.CTkEntry, valid: bool) -> None:
        """Set entry border color to indicate validation state."""
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
        CTkMessagebox(title="Warning", message="No HWID found. Generate it in Tab 1 first.", icon="warning")

    def _paste_hwid(self) -> None:
        try:
            clip = self.clipboard_get()
            self._var_hwid.set(clip.strip())
        except tk.TclError:
            CTkMessagebox(title="Warning", message="Clipboard is empty.", icon="warning")

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
            CTkMessagebox(title="Validation", message=msg, icon="cancel")
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

        if self._var_iat_auto.get() == "on":
            payload.set_auto_iat()
        else:
            try:
                date_obj = self._iat_manual_entry.get_date()
                dt = datetime(date_obj.year, date_obj.month, date_obj.day, tzinfo=timezone.utc)
                payload.iat = int(dt.timestamp())
            except Exception as e:
                CTkMessagebox(
                    title="Validation",
                    message=f"Invalid IAT date: {e}",
                    icon="cancel"
                )
                return None

        if self._var_exp_auto.get() == "on":
            payload.set_auto_exp(self._var_exp_days.get())
        else:
            try:
                date_obj = self._exp_manual_entry.get_date()
                dt = datetime(date_obj.year, date_obj.month, date_obj.day, 23, 59, 59, tzinfo=timezone.utc) # End of the day
                payload.exp = int(dt.timestamp())
            except Exception as e:
                CTkMessagebox(
                    title="Validation",
                    message=f"Invalid EXP date: {e}",
                    icon="cancel"
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
        self._var_iat_auto.set("on")
        self._var_exp_auto.set("on")
        self._var_exp_days.set(365)
        
        # Reset date entries to today
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
        win.title("Payload Preview (JSON)")
        win.geometry("500x500")
        
        text = ctk.CTkTextbox(win, wrap="word", font=ctk.CTkFont(family="Courier", size=13))
        text.pack(fill="both", expand=True, padx=20, pady=20)
        
        pretty = json.dumps(payload.to_dict(), indent=2)
        text.insert("1.0", pretty)
        text.configure(state="disabled")

    def _on_generate(self) -> None:
        payload = self._build_payload()
        if payload is None:
            return

        key_path = self._var_private_key_path.get()
        if not key_path:
            CTkMessagebox(title="Error", message="Select or generate a private key first.", icon="cancel")
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
            CTkMessagebox(title="Success", message=f"License written to:\n{save_path}", icon="check")
            if self.app:
                self.app.status(
                    f"License issued for {payload.client} \u2014 {save_path}",
                    "success",
                )
        except Exception as exc:
            CTkMessagebox(title="Error", message=f"Failed to generate license:\n{exc}", icon="cancel")
            if self.app:
                self.app.status(f"License generation failed: {exc}", "error")
