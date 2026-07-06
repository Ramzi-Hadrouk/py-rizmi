"""Tab 2 — Keypair Management: generate, load, and validate RSA keys."""
import os
import tempfile
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from CTkMessagebox import CTkMessagebox

from ...core.keypair import KeyPairManager
from ..theme import Color


class KeyManagerTab(ctk.CTkScrollableFrame):
    """Manage RSA keypairs — generate with configurable size, load from
    file or clipboard, and validate that private & public keys match."""

    def __init__(self, parent, app=None):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._temp_files: list[str] = []
        
        self.grid_columnconfigure(0, weight=1)
        self._build()

    # ===================== UI =====================

    def _build(self) -> None:
        self._build_generate_section()
        self._build_load_section()
        self._build_validate_section()

    # ---------- ① Generate ----------

    def _build_generate_section(self) -> None:
        f = ctk.CTkFrame(self, fg_color=("gray95", "gray13"), corner_radius=8)
        f.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 10))
        f.columnconfigure(1, weight=1)

        # Title
        ctk.CTkLabel(f, text="\u2460  Generate Keypair", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 10))

        # key size row
        ctk.CTkLabel(f, text="Key Size:", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=0, sticky="w", padx=20, pady=10
        )
        size_row = ctk.CTkFrame(f, fg_color="transparent")
        size_row.grid(row=1, column=1, sticky="w", padx=10, pady=10)
        
        self._var_key_size = ctk.StringVar(value=str(KeyPairManager.DEFAULT_KEY_SIZE))
        ctk.CTkComboBox(
            size_row,
            variable=self._var_key_size,
            values=[str(s) for s in KeyPairManager.KEY_SIZES],
            state="readonly",
            width=120,
        ).pack(side="left")
        
        ctk.CTkButton(
            size_row, text="\u2699  Generate", command=self._on_generate,
            width=120
        ).pack(side="left", padx=20)

        # private key
        ctk.CTkLabel(f, text="Private Key:", font=ctk.CTkFont(weight="bold")).grid(
            row=2, column=0, sticky="nw", padx=20, pady=(10, 0)
        )
        self._priv_text = ctk.CTkTextbox(
            f, height=120, font=ctk.CTkFont(family="Courier", size=13),
            fg_color=("white", "gray20"), border_width=1
        )
        self._priv_text.grid(row=2, column=1, sticky="ew", padx=(10, 20), pady=(10, 0))

        # public key
        ctk.CTkLabel(f, text="Public Key:", font=ctk.CTkFont(weight="bold")).grid(
            row=3, column=0, sticky="nw", padx=20, pady=(20, 0)
        )
        self._pub_text = ctk.CTkTextbox(
            f, height=100, font=ctk.CTkFont(family="Courier", size=13),
            fg_color=("white", "gray20"), border_width=1
        )
        self._pub_text.grid(row=3, column=1, sticky="ew", padx=(10, 20), pady=(20, 0))

        # save buttons + key info
        info_row = ctk.CTkFrame(f, fg_color="transparent")
        info_row.grid(row=4, column=1, sticky="w", padx=10, pady=20)
        
        ctk.CTkButton(
            info_row, text="\U0001f4be  Save Private", command=self._save_private,
            width=130, fg_color="#d97706", hover_color="#b45309"
        ).pack(side="left")
        
        ctk.CTkButton(
            info_row, text="\U0001f4be  Save Public", command=self._save_public,
            width=130
        ).pack(side="left", padx=20)
        
        self._gen_info = ctk.CTkLabel(info_row, text="", font=ctk.CTkFont(size=12))
        self._gen_info.pack(side="left")

    # ---------- ② Load ----------

    def _build_load_section(self) -> None:
        f = ctk.CTkFrame(self, fg_color=("gray95", "gray13"), corner_radius=8)
        f.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        f.columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="\u2461  Load Keys", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(20, 10))

        # Private Load
        ctk.CTkLabel(f, text="Private Key:", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=0, sticky="w", padx=20, pady=10
        )
        self._var_priv_path = ctk.StringVar()
        ctk.CTkEntry(
            f, textvariable=self._var_priv_path, state="readonly"
        ).grid(row=1, column=1, sticky="ew", padx=10, pady=10)
        
        btn_priv = ctk.CTkFrame(f, fg_color="transparent")
        btn_priv.grid(row=1, column=2, padx=(0, 20), pady=10)
        ctk.CTkButton(btn_priv, text="Browse\u2026", width=80, command=self._browse_priv).pack(side="left")
        ctk.CTkButton(btn_priv, text="Paste", width=70, fg_color="gray50", hover_color="gray40", command=self._paste_priv).pack(side="left", padx=(10, 0))

        # Public Load
        ctk.CTkLabel(f, text="Public Key:", font=ctk.CTkFont(weight="bold")).grid(
            row=2, column=0, sticky="w", padx=20, pady=(0, 20)
        )
        self._var_pub_path = ctk.StringVar()
        ctk.CTkEntry(
            f, textvariable=self._var_pub_path, state="readonly"
        ).grid(row=2, column=1, sticky="ew", padx=10, pady=(0, 20))
        
        btn_pub = ctk.CTkFrame(f, fg_color="transparent")
        btn_pub.grid(row=2, column=2, padx=(0, 20), pady=(0, 20))
        ctk.CTkButton(btn_pub, text="Browse\u2026", width=80, command=self._browse_pub).pack(side="left")
        ctk.CTkButton(btn_pub, text="Paste", width=70, fg_color="gray50", hover_color="gray40", command=self._paste_pub).pack(side="left", padx=(10, 0))

    # ---------- ③ Validate ----------

    def _build_validate_section(self) -> None:
        f = ctk.CTkFrame(self, fg_color=("gray95", "gray13"), corner_radius=8)
        f.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 30))
        f.columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="\u2462  Validate Keypair", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 10))

        # source selector
        ctk.CTkLabel(f, text="Source:", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=0, sticky="w", padx=20, pady=10
        )
        self._var_source = ctk.StringVar(value="generated")
        source_row = ctk.CTkFrame(f, fg_color="transparent")
        source_row.grid(row=1, column=1, sticky="w", padx=10, pady=10)
        
        ctk.CTkRadioButton(
            source_row, text="Generated above",
            variable=self._var_source, value="generated"
        ).pack(side="left")
        ctk.CTkRadioButton(
            source_row, text="Loaded files",
            variable=self._var_source, value="loaded"
        ).pack(side="left", padx=20)

        ctk.CTkButton(
            f, text="\u2705  Check Keys", command=self._on_validate,
            width=150
        ).grid(row=2, column=1, sticky="w", padx=10, pady=15)

        self._var_result = ctk.StringVar(value="Ready")
        self._result_label = ctk.CTkLabel(
            f, textvariable=self._var_result,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self._result_label.grid(row=3, column=1, sticky="w", padx=10, pady=(0, 20))

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

    def _cleanup_temp_files(self) -> None:
        for p in self._temp_files:
            try:
                os.unlink(p)
            except Exception:
                pass
        self._temp_files.clear()

    def _write_temp_pem(self, content: str) -> str | None:
        if "BEGIN " not in content:
            CTkMessagebox(title="Warning", message="Clipboard does not appear to contain a PEM key.", icon="warning")
            return None
        try:
            tmp = tempfile.NamedTemporaryFile(
                suffix=".pem", delete=False, mode="w"
            )
            tmp.write(content)
            tmp.close()
            self._temp_files.append(tmp.name)
            return tmp.name
        except Exception as exc:
            CTkMessagebox(title="Error", message=f"Failed to write temp key:\n{exc}", icon="cancel")
            return None

    # ---------- generate ----------

    def _on_generate(self) -> None:
        key_size = int(self._var_key_size.get())
        try:
            priv_pem, pub_pem = KeyPairManager.generate_keypair(key_size)
            self._priv_text.delete("1.0", tk.END)
            self._priv_text.insert("1.0", priv_pem)
            self._pub_text.delete("1.0", tk.END)
            self._pub_text.insert("1.0", pub_pem)
            self._gen_info.configure(
                text=f"\u2705 {key_size}-bit RSA pair generated",
                text_color=Color.SUCCESS,
            )
            self._var_result.set("Ready")
            self._result_label.configure(text_color=Color.FG)
            if self.app:
                self.app.status(f"{key_size}-bit keypair generated", "success")
        except Exception as exc:
            self._gen_info.configure(text=f"\u274c {exc}", text_color=Color.ERROR)
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
        if not path:
            return
        with open(path, "w") as f:
            f.write(pem)
        if self.app:
            self.app.status(f"Private key saved to {path}", "success")

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
        if not path:
            return
        with open(path, "w") as f:
            f.write(pem)
        if self.app:
            self.app.status(f"Public key saved to {path}", "success")

    # ---------- load ----------

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

    # ---------- validate ----------

    def _on_validate(self) -> None:
        source = self._var_source.get()

        if source == "generated":
            priv_pem = self._get_private_pem()
            pub_pem = self._get_public_pem()
        else:
            priv_pem = self._read_file(self._var_priv_path.get())
            pub_pem = self._read_file(self._var_pub_path.get())

        if not priv_pem or not pub_pem:
            self._var_result.set("\u26a0  No keys available in the selected source")
            self._result_label.configure(text_color=Color.WARNING)
            return

        priv_ok = KeyPairManager.validate_private_key(priv_pem)
        pub_ok = KeyPairManager.validate_public_key(pub_pem)

        if not priv_ok and not pub_ok:
            self._var_result.set("\u274c  Both keys are invalid PEM")
            self._result_label.configure(text_color=Color.ERROR)
            return
        if not priv_ok:
            self._var_result.set("\u274c  Private key is invalid")
            self._result_label.configure(text_color=Color.ERROR)
            return
        if not pub_ok:
            self._var_result.set("\u274c  Public key is invalid")
            self._result_label.configure(text_color=Color.ERROR)
            return

        if KeyPairManager.verify_keypair(priv_pem, pub_pem):
            size = KeyPairManager.get_key_size(priv_pem)
            self._var_result.set(f"\u2705  Keys match \u2014 {size}-bit RSA pair")
            self._result_label.configure(text_color=Color.SUCCESS)
            if self.app:
                self.app.status(f"Keys validated: {size}-bit matching pair", "success")
        else:
            self._var_result.set("\u274c  Keys do NOT match \u2014 they are from different keypairs")
            self._result_label.configure(text_color=Color.ERROR)
            if self.app:
                self.app.status("Keypair mismatch detected", "error")
