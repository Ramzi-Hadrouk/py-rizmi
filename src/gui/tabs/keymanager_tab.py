"""Tab 2 — Keypair Management: generate, load, and validate RSA keys."""
import os
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ...core.keypair import KeyPairManager
from ..theme import Color, Font, Pad


class KeyManagerTab(ttk.Frame):
    """Manage RSA keypairs — generate with configurable size, load from
    file or clipboard, and validate that private & public keys match."""

    def __init__(self, parent, app=None):
        super().__init__(parent)
        self.app = app
        self._temp_files: list[str] = []
        self._build()

    # ===================== UI =====================

    def _build(self) -> None:
        self._build_generate_section()
        self._build_load_section()
        self._build_validate_section()

    # ---------- ① Generate ----------

    def _build_generate_section(self) -> None:
        f = ttk.LabelFrame(
            self, text="\u2460  Generate Keypair", padding=Pad.LG
        )
        f.pack(fill="x", padx=Pad.XL, pady=(Pad.XL, Pad.SM))
        f.columnconfigure(1, weight=1)

        # key size row
        ttk.Label(f, text="Key Size:").grid(
            row=0, column=0, sticky="w", pady=Pad.SM
        )
        size_row = ttk.Frame(f)
        size_row.grid(row=0, column=1, sticky="w", padx=Pad.MD, pady=Pad.SM)
        self._var_key_size = tk.IntVar(value=KeyPairManager.DEFAULT_KEY_SIZE)
        ttk.Combobox(
            size_row,
            textvariable=self._var_key_size,
            values=KeyPairManager.KEY_SIZES,
            state="readonly",
            width=10,
        ).pack(side="left")
        ttk.Button(
            size_row, text="\u2699  Generate", command=self._on_generate
        ).pack(side="left", padx=Pad.MD)

        # private key
        ttk.Label(f, text="Private Key:").grid(
            row=1, column=0, sticky="nw", pady=(Pad.MD, 0)
        )
        priv_frame = ttk.Frame(f)
        priv_frame.grid(row=1, column=1, sticky="ew", padx=Pad.MD, pady=(Pad.MD, 0))
        priv_frame.columnconfigure(0, weight=1)
        self._priv_text = tk.Text(
            priv_frame, height=6, font=Font.MONO_SMALL, wrap="none"
        )
        self._priv_text.grid(row=0, column=0, sticky="ew")
        priv_scroll = ttk.Scrollbar(
            priv_frame, orient="vertical", command=self._priv_text.yview
        )
        priv_scroll.grid(row=0, column=1, sticky="ns")
        self._priv_text.config(yscrollcommand=priv_scroll.set)

        # public key
        ttk.Label(f, text="Public Key:").grid(
            row=2, column=0, sticky="nw", pady=(Pad.MD, 0)
        )
        pub_frame = ttk.Frame(f)
        pub_frame.grid(row=2, column=1, sticky="ew", padx=Pad.MD, pady=(Pad.MD, 0))
        pub_frame.columnconfigure(0, weight=1)
        self._pub_text = tk.Text(
            pub_frame, height=4, font=Font.MONO_SMALL, wrap="none"
        )
        self._pub_text.grid(row=0, column=0, sticky="ew")
        pub_scroll = ttk.Scrollbar(
            pub_frame, orient="vertical", command=self._pub_text.yview
        )
        pub_scroll.grid(row=0, column=1, sticky="ns")
        self._pub_text.config(yscrollcommand=pub_scroll.set)

        # save buttons + key info
        info_row = ttk.Frame(f)
        info_row.grid(row=3, column=1, sticky="w", padx=Pad.MD, pady=Pad.SM)
        ttk.Button(
            info_row, text="\U0001f4be  Save Private", command=self._save_private
        ).pack(side="left", padx=(0, Pad.MD))
        ttk.Button(
            info_row, text="\U0001f4be  Save Public", command=self._save_public
        ).pack(side="left", padx=(0, Pad.MD))
        self._gen_info = ttk.Label(info_row, text="", font=Font.SMALL)
        self._gen_info.pack(side="left", padx=Pad.MD)

    # ---------- ② Load ----------

    def _build_load_section(self) -> None:
        f = ttk.LabelFrame(
            self, text="\u2461  Load Keys", padding=Pad.LG
        )
        f.pack(fill="x", padx=Pad.XL, pady=Pad.SM)
        f.columnconfigure(1, weight=1)

        ttk.Label(f, text="Private Key:").grid(
            row=0, column=0, sticky="w", pady=Pad.SM
        )
        self._var_priv_path = tk.StringVar()
        ttk.Entry(
            f, textvariable=self._var_priv_path, state="readonly"
        ).grid(row=0, column=1, sticky="ew", padx=Pad.MD, pady=Pad.SM)
        btn_priv = ttk.Frame(f)
        btn_priv.grid(row=0, column=2, padx=(0, Pad.MD), pady=Pad.SM)
        ttk.Button(btn_priv, text="Browse\u2026",
                   command=self._browse_priv).pack(side="left")
        ttk.Button(btn_priv, text="Paste",
                   command=self._paste_priv).pack(side="left", padx=(Pad.SM, 0))

        ttk.Label(f, text="Public Key:").grid(
            row=1, column=0, sticky="w", pady=Pad.SM
        )
        self._var_pub_path = tk.StringVar()
        ttk.Entry(
            f, textvariable=self._var_pub_path, state="readonly"
        ).grid(row=1, column=1, sticky="ew", padx=Pad.MD, pady=Pad.SM)
        btn_pub = ttk.Frame(f)
        btn_pub.grid(row=1, column=2, padx=(0, Pad.MD), pady=Pad.SM)
        ttk.Button(btn_pub, text="Browse\u2026",
                   command=self._browse_pub).pack(side="left")
        ttk.Button(btn_pub, text="Paste",
                   command=self._paste_pub).pack(side="left", padx=(Pad.SM, 0))

    # ---------- ③ Validate ----------

    def _build_validate_section(self) -> None:
        f = ttk.LabelFrame(
            self, text="\u2462  Validate Keypair", padding=Pad.LG
        )
        f.pack(fill="x", padx=Pad.XL, pady=Pad.SM)
        f.columnconfigure(1, weight=1)

        # source selector
        ttk.Label(f, text="Source:").grid(
            row=0, column=0, sticky="w", pady=Pad.SM
        )
        self._var_source = tk.StringVar(value="generated")
        source_row = ttk.Frame(f)
        source_row.grid(row=0, column=1, sticky="w", padx=Pad.MD, pady=Pad.SM)
        ttk.Radiobutton(
            source_row, text="Generated above",
            variable=self._var_source, value="generated"
        ).pack(side="left")
        ttk.Radiobutton(
            source_row, text="Loaded files",
            variable=self._var_source, value="loaded"
        ).pack(side="left", padx=Pad.LG)

        ttk.Button(
            f, text="\u2705  Check Keys", command=self._on_validate
        ).grid(row=1, column=1, sticky="w", padx=Pad.MD, pady=Pad.SM)

        self._var_result = tk.StringVar(value="Ready")
        ttk.Label(
            f, textvariable=self._var_result,
            font=Font.BODY,
        ).grid(row=2, column=1, sticky="w", padx=Pad.MD, pady=Pad.SM)

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
        """Write *content* to a temp .pem file and return its path."""
        if "BEGIN " not in content:
            messagebox.showwarning(
                "Warning", "Clipboard does not appear to contain a PEM key."
            )
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
            messagebox.showerror("Error", f"Failed to write temp key:\n{exc}")
            return None

    # ---------- generate ----------

    def _on_generate(self) -> None:
        key_size = self._var_key_size.get()
        try:
            priv_pem, pub_pem = KeyPairManager.generate_keypair(key_size)
            self._priv_text.delete("1.0", tk.END)
            self._priv_text.insert("1.0", priv_pem)
            self._pub_text.delete("1.0", tk.END)
            self._pub_text.insert("1.0", pub_pem)
            self._gen_info.config(
                text=f"\u2705 {key_size}-bit RSA pair generated",
                foreground=Color.SUCCESS,
            )
            self._var_result.set("Ready")
            if self.app:
                self.app.status(f"{key_size}-bit keypair generated", "success")
        except Exception as exc:
            self._gen_info.config(text=f"\u274c {exc}", foreground=Color.ERROR)
            if self.app:
                self.app.status("Keypair generation failed", "error")

    def _save_private(self) -> None:
        pem = self._get_private_pem()
        if not pem:
            messagebox.showwarning("Warning", "Generate a keypair first.")
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
            messagebox.showwarning("Warning", "Generate a keypair first.")
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
            messagebox.showwarning("Warning", "Clipboard is empty.")
            return
        tmp = self._write_temp_pem(clip)
        if tmp:
            self._var_priv_path.set(tmp)

    def _paste_pub(self) -> None:
        try:
            clip = self.clipboard_get().strip()
        except tk.TclError:
            messagebox.showwarning("Warning", "Clipboard is empty.")
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
            self._var_result.set(
                "\u26a0  No keys available in the selected source"
            )
            return

        priv_ok = KeyPairManager.validate_private_key(priv_pem)
        pub_ok = KeyPairManager.validate_public_key(pub_pem)

        if not priv_ok and not pub_ok:
            self._var_result.set("\u274c  Both keys are invalid PEM")
            return
        if not priv_ok:
            self._var_result.set("\u274c  Private key is invalid")
            return
        if not pub_ok:
            self._var_result.set("\u274c  Public key is invalid")
            return

        if KeyPairManager.verify_keypair(priv_pem, pub_pem):
            size = KeyPairManager.get_key_size(priv_pem)
            self._var_result.set(
                f"\u2705  Keys match \u2014 {size}-bit RSA pair"
            )
            if self.app:
                self.app.status(f"Keys validated: {size}-bit matching pair", "success")
        else:
            self._var_result.set(
                "\u274c  Keys do NOT match \u2014 they are from different keypairs"
            )
            if self.app:
                self.app.status("Keypair mismatch detected", "error")
