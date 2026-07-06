"""Tab 2 — Keypair Management: generate, load, and validate RSA keys."""
import os
import tempfile
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from CTkMessagebox import CTkMessagebox

from ...core.keypair import KeyPairManager
from ..theme import Color
from ..widgets.step_card import StepCard


class KeyManagerTab(ctk.CTkScrollableFrame):
    """Manage RSA keypairs — generate with configurable size, load from
    file or clipboard, and validate that private & public keys match."""

    def __init__(self, parent, app=None):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._temp_files: list[str] = []
        self._active_source = "generate"

        self.grid_columnconfigure(0, weight=1)
        self._build()

    # ===================== UI =====================

    def _build(self) -> None:
        self._build_source_card()
        self._build_validate_card()

    # ─── STEP 1: Key Source ───────────────────────────────────────────

    def _build_source_card(self) -> None:
        card = StepCard(self, step=1, title="Key Source")
        card.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 8))
        card.body.columnconfigure(0, weight=1)

        # Segmented switcher
        seg = ctk.CTkSegmentedButton(
            card.body,
            values=["⚙  Generate New Keypair", "📂  Load Existing Keys"],
            command=self._on_source_change,
            font=ctk.CTkFont(size=13),
            height=36,
        )
        seg.set("⚙  Generate New Keypair")
        seg.grid(row=0, column=0, sticky="ew", pady=(0, 14))

        # ── Panel A: Generate ──────────────────────────────────────────
        self._gen_panel = ctk.CTkFrame(card.body, fg_color="transparent")
        self._gen_panel.grid(row=1, column=0, sticky="nsew")
        self._gen_panel.columnconfigure(0, weight=1)
        self._gen_panel.columnconfigure(1, weight=1)
        self._build_generate_panel(self._gen_panel)

        # ── Panel B: Load ──────────────────────────────────────────────
        self._load_panel = ctk.CTkFrame(card.body, fg_color="transparent")
        # NOT gridded initially — shown on demand
        self._load_panel.columnconfigure(0, weight=1)
        self._build_load_panel(self._load_panel)

    # ── Generate panel ────────────────────────────────────────────────

    def _build_generate_panel(self, parent: ctk.CTkFrame) -> None:
        # Key size + Generate button row
        ctrl = ctk.CTkFrame(parent, fg_color="transparent")
        ctrl.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        ctk.CTkLabel(ctrl, text="Key Size:", font=ctk.CTkFont(weight="bold"),
                     text_color="gray50").pack(side="left")

        self._var_key_size = ctk.StringVar(value=str(KeyPairManager.DEFAULT_KEY_SIZE))
        ctk.CTkComboBox(
            ctrl,
            variable=self._var_key_size,
            values=[str(s) for s in KeyPairManager.KEY_SIZES],
            state="readonly",
            width=110,
        ).pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            ctrl, text="⚙  Generate Keypair", command=self._on_generate,
            width=160, height=34, font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left", padx=16)

        self._gen_info = ctk.CTkLabel(ctrl, text="", font=ctk.CTkFont(size=12))
        self._gen_info.pack(side="left")

        # ── Private Key ────────────────────────────────────────────────
        priv_card = ctk.CTkFrame(parent, fg_color=("gray88", "gray17"), corner_radius=8)
        priv_card.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(0, 10))
        priv_card.columnconfigure(0, weight=1)

        hdr_priv = ctk.CTkFrame(priv_card, fg_color="transparent")
        hdr_priv.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        ctk.CTkLabel(hdr_priv, text="🔒", font=ctk.CTkFont(size=14)).pack(side="left")
        ctk.CTkLabel(hdr_priv, text="  Private Key",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")

        self._priv_text = ctk.CTkTextbox(
            priv_card, height=140,
            font=ctk.CTkFont(family="Courier", size=11),
            fg_color=("white", "gray20"), border_width=1,
            wrap="none",
        )
        self._priv_text.grid(row=1, column=0, sticky="ew", padx=12)

        priv_btns = ctk.CTkFrame(priv_card, fg_color="transparent")
        priv_btns.grid(row=2, column=0, sticky="w", padx=12, pady=(6, 12))
        ctk.CTkButton(
            priv_btns, text="💾  Save", command=self._save_private,
            width=90, height=30, fg_color="#d97706", hover_color="#b45309",
        ).pack(side="left")
        ctk.CTkButton(
            priv_btns, text="📋  Copy", command=self._copy_private,
            width=80, height=30, fg_color="gray50", hover_color="gray40",
        ).pack(side="left", padx=8)

        # ── Public Key ─────────────────────────────────────────────────
        pub_card = ctk.CTkFrame(parent, fg_color=("gray88", "gray17"), corner_radius=8)
        pub_card.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=(0, 10))
        pub_card.columnconfigure(0, weight=1)

        hdr_pub = ctk.CTkFrame(pub_card, fg_color="transparent")
        hdr_pub.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        ctk.CTkLabel(hdr_pub, text="🔓", font=ctk.CTkFont(size=14)).pack(side="left")
        ctk.CTkLabel(hdr_pub, text="  Public Key",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")

        self._pub_text = ctk.CTkTextbox(
            pub_card, height=140,
            font=ctk.CTkFont(family="Courier", size=11),
            fg_color=("white", "gray20"), border_width=1,
            wrap="none",
        )
        self._pub_text.grid(row=1, column=0, sticky="ew", padx=12)

        pub_btns = ctk.CTkFrame(pub_card, fg_color="transparent")
        pub_btns.grid(row=2, column=0, sticky="w", padx=12, pady=(6, 12))
        ctk.CTkButton(
            pub_btns, text="💾  Save", command=self._save_public,
            width=90, height=30,
        ).pack(side="left")
        ctk.CTkButton(
            pub_btns, text="📋  Copy", command=self._copy_public,
            width=80, height=30, fg_color="gray50", hover_color="gray40",
        ).pack(side="left", padx=8)

    # ── Load panel ────────────────────────────────────────────────────

    def _build_load_panel(self, parent: ctk.CTkFrame) -> None:
        tip = ctk.CTkLabel(
            parent,
            text="Browse for .pem files on disk, or paste PEM content directly from clipboard.",
            text_color="gray50", font=ctk.CTkFont(size=12), justify="left",
        )
        tip.grid(row=0, column=0, sticky="w", pady=(0, 12))

        # Private Load
        self._var_priv_path = ctk.StringVar()
        self._build_file_row(parent, row=1,
                             label="🔒  Private Key File:",
                             var=self._var_priv_path,
                             browse_cmd=self._browse_priv,
                             paste_cmd=self._paste_priv)

        # Separator
        ctk.CTkFrame(parent, height=1, fg_color=("gray80", "gray30")).grid(
            row=2, column=0, sticky="ew", pady=12)

        # Public Load
        self._var_pub_path = ctk.StringVar()
        self._build_file_row(parent, row=3,
                             label="🔓  Public Key File:",
                             var=self._var_pub_path,
                             browse_cmd=self._browse_pub,
                             paste_cmd=self._paste_pub)

    def _build_file_row(self, parent, row, label, var, browse_cmd, paste_cmd):
        ctk.CTkLabel(parent, text=label,
                     font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=row, column=0, sticky="w", pady=(0, 6))

        inner = ctk.CTkFrame(parent, fg_color="transparent")
        inner.grid(row=row + 1, column=0, sticky="ew", pady=(0, 4))
        inner.columnconfigure(0, weight=1)

        ctk.CTkEntry(inner, textvariable=var, state="readonly").grid(
            row=0, column=0, sticky="ew")
        ctk.CTkButton(inner, text="Browse…", width=80,
                      command=browse_cmd).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(inner, text="Paste", width=70,
                      fg_color="gray50", hover_color="gray40",
                      command=paste_cmd).grid(row=0, column=2, padx=(8, 0))

    # ─── STEP 2: Validate ─────────────────────────────────────────────

    def _build_validate_card(self) -> None:
        card = StepCard(self, step=2, title="Validate Keypair")
        card.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 24))
        card.body.columnconfigure(0, weight=1)

        desc = ctk.CTkLabel(
            card.body,
            text="Confirm that the private and public keys belong to the same RSA keypair.",
            text_color="gray50", font=ctk.CTkFont(size=12),
        )
        desc.grid(row=0, column=0, sticky="w", pady=(0, 12))

        action = ctk.CTkFrame(card.body, fg_color="transparent")
        action.grid(row=1, column=0, sticky="ew")

        ctk.CTkButton(
            action,
            text="✅  Validate Keypair",
            command=self._on_validate,
            width=180, height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left")

        self._var_result = ctk.StringVar(value="")
        self._result_label = ctk.CTkLabel(
            action,
            textvariable=self._var_result,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self._result_label.pack(side="left", padx=20)

    # ===================== panel switcher =====================

    def _on_source_change(self, value: str) -> None:
        if "Generate" in value:
            self._active_source = "generate"
            self._load_panel.grid_remove()
            self._gen_panel.grid(row=1, column=0, sticky="nsew")
        else:
            self._active_source = "load"
            self._gen_panel.grid_remove()
            self._load_panel.grid(row=1, column=0, sticky="nsew")

    # ===================== helpers =====================

    def _get_private_pem(self) -> str:
        return self._priv_text.get("1.0", tk.END).strip()

    def _get_public_pem(self) -> str:
        return self._pub_text.get("1.0", tk.END).strip()

    def _read_file(self, path: str) -> str:
        if not path:
            return ""
        try:
            with open(path) as f:
                return f.read().strip()
        except Exception:
            return ""

    def _write_temp_pem(self, content: str) -> str | None:
        if "BEGIN " not in content:
            CTkMessagebox(title="Warning",
                          message="Clipboard does not appear to contain a PEM key.",
                          icon="warning")
            return None
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".pem", delete=False, mode="w")
            tmp.write(content)
            tmp.close()
            self._temp_files.append(tmp.name)
            return tmp.name
        except Exception as exc:
            CTkMessagebox(title="Error",
                          message=f"Failed to write temp key:\n{exc}", icon="cancel")
            return None

    # ── generate ──────────────────────────────────────────────────────

    def _on_generate(self) -> None:
        key_size = int(self._var_key_size.get())
        try:
            priv_pem, pub_pem = KeyPairManager.generate_keypair(key_size)
            self._priv_text.delete("1.0", tk.END)
            self._priv_text.insert("1.0", priv_pem)
            self._pub_text.delete("1.0", tk.END)
            self._pub_text.insert("1.0", pub_pem)
            self._gen_info.configure(
                text=f"✅  {key_size}-bit RSA keypair ready",
                text_color=Color.SUCCESS,
            )
            self._var_result.set("")
            if self.app:
                self.app.status(f"{key_size}-bit keypair generated", "success")
        except Exception as exc:
            self._gen_info.configure(text=f"❌  {exc}", text_color=Color.ERROR)
            if self.app:
                self.app.status("Keypair generation failed", "error")

    def _save_private(self) -> None:
        pem = self._get_private_pem()
        if not pem:
            CTkMessagebox(title="Warning", message="Generate a keypair first.", icon="warning")
            return
        path = filedialog.asksaveasfilename(
            title="Save Private Key",
            defaultextension=".pem",
            filetypes=[("PEM files", "*.pem"), ("All files", "*.*")],
        )
        if path:
            with open(path, "w") as f:
                f.write(pem)
            if self.app:
                self.app.status(f"Private key saved → {path}", "success")

    def _save_public(self) -> None:
        pem = self._get_public_pem()
        if not pem:
            CTkMessagebox(title="Warning", message="Generate a keypair first.", icon="warning")
            return
        path = filedialog.asksaveasfilename(
            title="Save Public Key",
            defaultextension=".pem",
            filetypes=[("PEM files", "*.pem"), ("All files", "*.*")],
        )
        if path:
            with open(path, "w") as f:
                f.write(pem)
            if self.app:
                self.app.status(f"Public key saved → {path}", "success")

    def _copy_private(self) -> None:
        pem = self._get_private_pem()
        if pem:
            self.clipboard_clear()
            self.clipboard_append(pem)
            self._gen_info.configure(text="📋  Private key copied", text_color=Color.SUCCESS)
        else:
            CTkMessagebox(title="Warning", message="Generate a keypair first.", icon="warning")

    def _copy_public(self) -> None:
        pem = self._get_public_pem()
        if pem:
            self.clipboard_clear()
            self.clipboard_append(pem)
            self._gen_info.configure(text="📋  Public key copied", text_color=Color.SUCCESS)
        else:
            CTkMessagebox(title="Warning", message="Generate a keypair first.", icon="warning")

    # ── load ──────────────────────────────────────────────────────────

    def _browse_priv(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Private Key",
            filetypes=[("PEM files", "*.pem"), ("All files", "*.*")],
        )
        if path:
            self._var_priv_path.set(path)

    def _browse_pub(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Public Key",
            filetypes=[("PEM files", "*.pem"), ("All files", "*.*")],
        )
        if path:
            self._var_pub_path.set(path)

    def _paste_priv(self) -> None:
        try:
            clip = self.clipboard_get().strip()
        except tk.TclError:
            CTkMessagebox(title="Warning", message="Clipboard is empty.", icon="warning")
            return
        tmp = self._write_temp_pem(clip)
        if tmp:
            self._var_priv_path.set(tmp)

    def _paste_pub(self) -> None:
        try:
            clip = self.clipboard_get().strip()
        except tk.TclError:
            CTkMessagebox(title="Warning", message="Clipboard is empty.", icon="warning")
            return
        tmp = self._write_temp_pem(clip)
        if tmp:
            self._var_pub_path.set(tmp)

    # ── validate ──────────────────────────────────────────────────────

    def _on_validate(self) -> None:
        if self._active_source == "generate":
            priv_pem = self._get_private_pem()
            pub_pem = self._get_public_pem()
        else:
            priv_pem = self._read_file(self._var_priv_path.get())
            pub_pem = self._read_file(self._var_pub_path.get())

        if not priv_pem or not pub_pem:
            self._var_result.set("⚠  No keys available in active panel")
            self._result_label.configure(text_color=Color.WARNING)
            return

        priv_ok = KeyPairManager.validate_private_key(priv_pem)
        pub_ok = KeyPairManager.validate_public_key(pub_pem)

        if not priv_ok and not pub_ok:
            self._set_result("❌  Both keys are invalid PEM", Color.ERROR)
            return
        if not priv_ok:
            self._set_result("❌  Private key is invalid PEM", Color.ERROR)
            return
        if not pub_ok:
            self._set_result("❌  Public key is invalid PEM", Color.ERROR)
            return

        if KeyPairManager.verify_keypair(priv_pem, pub_pem):
            size = KeyPairManager.get_key_size(priv_pem)
            self._set_result(f"✅  Keys match — {size}-bit RSA pair", Color.SUCCESS)
            if self.app:
                self.app.status(f"Keys validated: {size}-bit pair", "success")
        else:
            self._set_result("❌  Keys do NOT match — different keypairs", Color.ERROR)
            if self.app:
                self.app.status("Keypair mismatch detected", "error")

    def _set_result(self, text: str, color: str) -> None:
        self._var_result.set(text)
        self._result_label.configure(text_color=color)
