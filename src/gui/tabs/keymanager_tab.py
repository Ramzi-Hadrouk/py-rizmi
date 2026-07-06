"""Tab 2 — Keypair Management: generate, load, and validate RSA keys."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ...core.keypair import KeyPairManager


class KeyManagerTab(ttk.Frame):
    """Manage RSA keypairs — generate with configurable size, load from
    file or clipboard, and validate that private & public keys match."""

    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    # ===================== UI =====================

    def _build(self) -> None:
        self._build_generate_section()
        self._build_load_section()
        self._build_validate_section()

    # ---------- ① Generate ----------

    def _build_generate_section(self) -> None:
        f = ttk.LabelFrame(
            self, text="\u2460  Generate Keypair", padding=12
        )
        f.pack(fill="x", padx=16, pady=(16, 6))

        ttk.Label(f, text="Key Size:").grid(
            row=0, column=0, sticky="w", pady=4
        )
        self._var_key_size = tk.IntVar(value=KeyPairManager.DEFAULT_KEY_SIZE)
        ttk.Combobox(
            f,
            textvariable=self._var_key_size,
            values=KeyPairManager.KEY_SIZES,
            state="readonly",
            width=10,
        ).grid(row=0, column=1, sticky="w", padx=8, pady=4)
        ttk.Button(
            f, text="Generate", command=self._on_generate
        ).grid(row=0, column=2, padx=8, pady=4)

        # private key text area
        ttk.Label(f, text="Private Key:").grid(
            row=1, column=0, sticky="nw", pady=(8, 0)
        )
        self._priv_text = tk.Text(f, height=7, width=62, font=("Consolas", 9))
        self._priv_text.grid(
            row=1, column=1, columnspan=2, sticky="w", padx=8, pady=(8, 2)
        )
        self._priv_scroll = ttk.Scrollbar(f, orient="vertical",
                                          command=self._priv_text.yview)
        self._priv_scroll.grid(row=1, column=3, sticky="ns", pady=(8, 2))
        self._priv_text.config(yscrollcommand=self._priv_scroll.set)

        btn_row = ttk.Frame(f)
        btn_row.grid(row=2, column=1, columnspan=2, sticky="w", padx=8, pady=2)
        ttk.Button(
            btn_row, text="Save Private Key",
            command=self._save_private
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            btn_row, text="Save Public Key",
            command=self._save_public
        ).pack(side="left")

        # public key text area
        ttk.Label(f, text="Public Key:").grid(
            row=3, column=0, sticky="nw", pady=(8, 0)
        )
        self._pub_text = tk.Text(f, height=4, width=62, font=("Consolas", 9))
        self._pub_text.grid(
            row=3, column=1, columnspan=2, sticky="w", padx=8, pady=(8, 2)
        )
        self._pub_scroll = ttk.Scrollbar(f, orient="vertical",
                                         command=self._pub_text.yview)
        self._pub_scroll.grid(row=3, column=3, sticky="ns", pady=(8, 2))
        self._pub_text.config(yscrollcommand=self._pub_scroll.set)

    # ---------- ② Load ----------

    def _build_load_section(self) -> None:
        f = ttk.LabelFrame(
            self, text="\u2461  Load Keys", padding=12
        )
        f.pack(fill="x", padx=16, pady=6)

        # private key row
        ttk.Label(f, text="Private Key:").grid(
            row=0, column=0, sticky="w", pady=4
        )
        self._var_priv_path = tk.StringVar()
        ttk.Entry(
            f, textvariable=self._var_priv_path, width=50, state="readonly"
        ).grid(row=0, column=1, sticky="w", padx=8, pady=4)
        ttk.Button(
            f, text="Browse\u2026", command=self._browse_priv
        ).grid(row=0, column=2, pady=4)
        ttk.Button(
            f, text="Paste", command=self._paste_priv
        ).grid(row=0, column=3, padx=(4, 0), pady=4)

        # public key row
        ttk.Label(f, text="Public Key:").grid(
            row=1, column=0, sticky="w", pady=4
        )
        self._var_pub_path = tk.StringVar()
        ttk.Entry(
            f, textvariable=self._var_pub_path, width=50, state="readonly"
        ).grid(row=1, column=1, sticky="w", padx=8, pady=4)
        ttk.Button(
            f, text="Browse\u2026", command=self._browse_pub
        ).grid(row=1, column=2, pady=4)
        ttk.Button(
            f, text="Paste", command=self._paste_pub
        ).grid(row=1, column=3, padx=(4, 0), pady=4)

    # ---------- ③ Validate ----------

    def _build_validate_section(self) -> None:
        f = ttk.LabelFrame(
            self, text="\u2462  Validate Pair", padding=12
        )
        f.pack(fill="x", padx=16, pady=6)

        ttk.Button(
            f, text="\u2705  Check Keys",
            command=self._on_validate
        ).pack(side="left", padx=(0, 12))

        self._var_result = tk.StringVar(value="Ready")
        ttk.Label(
            f, textvariable=self._var_result,
            font=("TkDefaultFont", 10, "bold")
        ).pack(side="left", fill="x", expand=True)

    # ===================== helpers =====================

    def _get_private_pem(self) -> str:
        """Return private key PEM from generate area."""
        return self._priv_text.get("1.0", tk.END).strip()

    def _get_public_pem(self) -> str:
        """Return public key PEM from generate area."""
        return self._pub_text.get("1.0", tk.END).strip()

    def _get_loaded_private_pem(self) -> str:
        """Return private key PEM from load area (file or paste)."""
        path = self._var_priv_path.get()
        if not path:
            return ""
        try:
            with open(path) as f:
                return f.read().strip()
        except Exception:
            return ""

    def _get_loaded_public_pem(self) -> str:
        """Return public key PEM from load area (file or paste)."""
        path = self._var_pub_path.get()
        if not path:
            return ""
        try:
            with open(path) as f:
                return f.read().strip()
        except Exception:
            return ""

    # ---------- generate ----------

    def _on_generate(self) -> None:
        key_size = self._var_key_size.get()
        try:
            priv_pem, pub_pem = KeyPairManager.generate_keypair(key_size)
            self._priv_text.delete("1.0", tk.END)
            self._priv_text.insert("1.0", priv_pem)
            self._pub_text.delete("1.0", tk.END)
            self._pub_text.insert("1.0", pub_pem)
            self._var_result.set(
                f"\u2705 {key_size}-bit keypair generated"
            )
        except Exception as exc:
            messagebox.showerror("Error", f"Generation failed:\n{exc}")

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
        messagebox.showinfo("Saved", f"Private key written to:\n{path}")

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
        messagebox.showinfo("Saved", f"Public key written to:\n{path}")

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

    @staticmethod
    def _write_temp_pem(content: str) -> str | None:
        """Write *content* to a temp .pem file and return its path."""
        import tempfile
        try:
            if "KEY" not in content:
                messagebox.showwarning(
                    "Warning", "Clipboard does not appear to contain a PEM key."
                )
                return None
            tmp = tempfile.NamedTemporaryFile(
                suffix=".pem", delete=False, mode="w"
            )
            tmp.write(content)
            tmp.close()
            return tmp.name
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to write temp key:\n{exc}")
            return None

    # ---------- validate ----------

    def _on_validate(self) -> None:
        # Try generate-area keys first, fall back to loaded keys
        priv_pem = self._get_private_pem()
        pub_pem = self._get_public_pem()

        if not priv_pem or not pub_pem:
            priv_pem = self._get_loaded_private_pem()
            pub_pem = self._get_loaded_public_pem()

        if not priv_pem or not pub_pem:
            self._var_result.set("\u26a0  No keys to validate — generate or load keys first")
            return

        # validate individual format
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

        # check pair match
        if KeyPairManager.verify_keypair(priv_pem, pub_pem):
            size = KeyPairManager.get_key_size(priv_pem)
            self._var_result.set(
                f"\u2705  Keys match \u2014 {size}-bit RSA pair"
            )
        else:
            self._var_result.set(
                "\u274c  Keys do NOT match \u2014 they are from different keypairs"
            )
