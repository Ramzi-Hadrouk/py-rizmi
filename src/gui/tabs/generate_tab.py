"""Tab 2 — License Generation with fully dynamic payload fields (Task 4.4)."""
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime, timezone

from ...core.keypair import KeyPairManager
from ...core.license_issuer import LicenseIssuer
from ...core.license_token import LicensePayload
from ..widgets.dynamic_list import DynamicListWidget


class GenerateTab(ttk.Frame):
    """Every payload field is a bound input widget — zero hard-coded values."""

    def __init__(self, parent, get_hwid_cb=None):
        super().__init__(parent)
        self._get_hwid_cb = get_hwid_cb  # callback to fetch HWID from Tab 1

        # --- input variables (all dynamic, no hard-coded payload) ---
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
        self._build()

    # ===================== UI =====================

    def _build(self) -> None:
        canvas = tk.Canvas(self, highlightthickness=0, bg="#f0f0f0")
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
        f = ttk.LabelFrame(parent, text="\u2460  Signing Key (Private Key)", padding=12)
        f.pack(fill="x", padx=16, pady=(16, 6))

        ttk.Label(f, text="Private Key File:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(f, textvariable=self._var_private_key_path,
                  width=48, state="readonly").grid(row=0, column=1, sticky="w", padx=8, pady=4)
        ttk.Button(f, text="Browse\u2026", command=self._browse_private_key).grid(row=0, column=2, pady=4)
        ttk.Button(f, text="Generate New Keypair",
                   command=self._generate_keypair).grid(row=1, column=1, sticky="w", pady=8)

    # ---------- payload section ----------

    def _build_payload_section(self, parent) -> None:
        f = ttk.LabelFrame(parent, text="\u2461  License Payload  (all fields are inputs)", padding=12)
        f.pack(fill="x", padx=16, pady=6)

        r = 0

        # client
        ttk.Label(f, text="Client / Deployment:").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Entry(f, textvariable=self._var_client, width=48).grid(row=r, column=1, sticky="w", padx=8, pady=4)
        r += 1

        # license_id
        ttk.Label(f, text="License ID:").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Entry(f, textvariable=self._var_license_id, width=48).grid(row=r, column=1, sticky="w", padx=8, pady=4)
        r += 1

        # hwid
        ttk.Label(f, text="HWID:").grid(row=r, column=0, sticky="w", pady=4)
        hwid_row = ttk.Frame(f)
        hwid_row.grid(row=r, column=1, sticky="w", padx=8, pady=4)
        ttk.Entry(hwid_row, textvariable=self._var_hwid, width=42).pack(side="left")
        ttk.Button(hwid_row, text="From Tab 1", width=10,
                   command=self._pull_hwid).pack(side="left", padx=4)
        ttk.Button(hwid_row, text="Paste", width=6,
                   command=self._paste_hwid).pack(side="left")
        r += 1

        # features (dynamic list)
        ttk.Label(f, text="Features:").grid(row=r, column=0, sticky="nw", pady=4)
        feat_container = ttk.Frame(f)
        feat_container.grid(row=r, column=1, sticky="w", padx=8, pady=4)
        self._features_widget = DynamicListWidget(feat_container, label="Feature")
        self._features_widget.pack(fill="x")
        r += 1

        # max_clients
        ttk.Label(f, text="Max Clients:").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Spinbox(f, from_=1, to=99999, textvariable=self._var_max_clients,
                    width=10).grid(row=r, column=1, sticky="w", padx=8, pady=4)
        r += 1

        # mode
        ttk.Label(f, text="Mode:").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Combobox(f, textvariable=self._var_mode, values=["offline", "online"],
                     state="readonly", width=12).grid(row=r, column=1, sticky="w", padx=8, pady=4)
        r += 1

        # server_url
        ttk.Label(f, text="Server URL:").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Entry(f, textvariable=self._var_server_url, width=48).grid(row=r, column=1, sticky="w", padx=8, pady=4)
        r += 1

        # grace_days
        ttk.Label(f, text="Grace Days:").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Spinbox(f, from_=0, to=365, textvariable=self._var_grace_days,
                    width=10).grid(row=r, column=1, sticky="w", padx=8, pady=4)
        r += 1

        # iat
        ttk.Label(f, text="Issued At (iat):").grid(row=r, column=0, sticky="w", pady=4)
        iat_row = ttk.Frame(f)
        iat_row.grid(row=r, column=1, sticky="w", padx=8, pady=4)
        ttk.Checkbutton(iat_row, text="Auto (now)", variable=self._var_iat_auto,
                        command=self._toggle_iat).pack(side="left")
        self._iat_manual_entry = ttk.Entry(iat_row, textvariable=self._var_iat_manual,
                                           width=25, state="disabled")
        self._iat_manual_entry.pack(side="left", padx=8)
        r += 1

        # exp
        ttk.Label(f, text="Expiration (exp):").grid(row=r, column=0, sticky="w", pady=4)
        exp_row = ttk.Frame(f)
        exp_row.grid(row=r, column=1, sticky="w", padx=8, pady=4)
        ttk.Checkbutton(exp_row, text="Auto", variable=self._var_exp_auto,
                        command=self._toggle_exp).pack(side="left")
        ttk.Label(exp_row, text="days:").pack(side="left", padx=(8, 2))
        ttk.Spinbox(exp_row, from_=1, to=3650, textvariable=self._var_exp_days,
                    width=8).pack(side="left")
        ttk.Label(exp_row, text="or manual:").pack(side="left", padx=(12, 2))
        self._exp_manual_entry = ttk.Entry(exp_row, textvariable=self._var_exp_manual,
                                           width=25, state="disabled")
        self._exp_manual_entry.pack(side="left")
        r += 1

    # ---------- action section ----------

    def _build_action_section(self, parent) -> None:
        f = ttk.Frame(parent)
        f.pack(fill="x", padx=16, pady=16)
        ttk.Button(f, text="\U0001f510  Generate License",
                   command=self._on_generate).pack(side="left", padx=4)
        ttk.Button(f, text="\U0001f4cb  Preview Payload (JSON)",
                   command=self._on_preview).pack(side="left", padx=4)

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

    def _browse_private_key(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Private Key",
            filetypes=[("PEM files", "*.pem"), ("All files", "*.*")],
        )
        if path:
            self._var_private_key_path.set(path)

    def _generate_keypair(self) -> None:
        path = filedialog.askdirectory(title="Select directory for keypair")
        if not path:
            return
        priv = f"{path}/private_key.pem"
        pub = f"{path}/public_key.pem"
        KeyPairManager.save_keypair(priv, pub)
        self._var_private_key_path.set(priv)
        messagebox.showinfo("Keypair Generated",
                            f"Private: {priv}\nPublic: {pub}")

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

    # ===================== payload building =====================

    def _build_payload(self) -> LicensePayload | None:
        """Read every input widget and return a LicensePayload (or None on error)."""

        client = self._var_client.get().strip()
        if not client:
            messagebox.showerror("Validation", "Client / Deployment Name is required.")
            return None

        license_id = self._var_license_id.get().strip()
        if not license_id:
            messagebox.showerror("Validation", "License ID is required.")
            return None

        hwid = self._var_hwid.get().strip()
        if not hwid:
            messagebox.showerror("Validation", "HWID is required.")
            return None

        payload = LicensePayload(
            client=client,
            license_id=license_id,
            hwid=hwid,
            features=self._features_widget.get_values(),
            max_clients=self._var_max_clients.get(),
            mode=self._var_mode.get(),
            server_url=self._var_server_url.get().strip(),
            grace_days=self._var_grace_days.get(),
        )

        # iat
        if self._var_iat_auto.get():
            payload.set_auto_iat()
        else:
            iat_str = self._var_iat_manual.get().strip()
            try:
                payload.iat = self._parse_timestamp(iat_str)
            except ValueError:
                messagebox.showerror("Validation",
                                     f"Invalid IAT format: {iat_str}\n"
                                     "Use epoch seconds or ISO 8601 (UTC).")
                return None

        # exp
        if self._var_exp_auto.get():
            payload.set_auto_exp(self._var_exp_days.get())
        else:
            exp_str = self._var_exp_manual.get().strip()
            try:
                payload.exp = self._parse_timestamp(exp_str)
            except ValueError:
                messagebox.showerror("Validation",
                                     f"Invalid EXP format: {exp_str}\n"
                                     "Use epoch seconds or ISO 8601 (UTC).")
                return None

        return payload

    @staticmethod
    def _parse_timestamp(s: str) -> int:
        """Accept epoch int or ISO-8601 string \u2192 epoch int."""
        s = s.strip()
        if s.isdigit():
            return int(s)
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())

    # ===================== actions =====================

    def _on_preview(self) -> None:
        payload = self._build_payload()
        if payload is None:
            return
        win = tk.Toplevel(self)
        win.title("Payload Preview (JSON)")
        win.geometry("500x500")
        text = tk.Text(win, wrap="word", font=("Consolas", 11))
        text.pack(fill="both", expand=True, padx=8, pady=8)
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
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to generate license:\n{exc}")
