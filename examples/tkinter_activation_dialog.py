"""Tkinter activation dialog — paste-or-file license entry in ~60 lines.

Run me:
    python examples/tkinter_activation_dialog.py

The developer's own UI hosts the entry widgets; py-rizmi only validates.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

from py_rizmi import LicenseGate, pin_fingerprint

VENDOR_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
...your public key...
-----END PUBLIC KEY-----"""
VENDOR_KEY_FINGERPRINT = "...fingerprint from `rizmi keys fingerprint`..."

pin_fingerprint(VENDOR_PUBLIC_KEY, VENDOR_KEY_FINGERPRINT)

gate = LicenseGate(
    app_name="MyGuiApp",
    public_key=VENDOR_PUBLIC_KEY,
    config_dir=Path.home() / ".config" / "MyGuiApp",
)


def on_paste() -> None:
    result = gate.activate_token(paste_box.get("1.0", "end").strip())
    show(result)


def on_pick_file() -> None:
    path = filedialog.askopenfilename(filetypes=[("License files", "*.lic"), ("All files", "*")])
    if path:
        show(gate.activate_file(path))


def show(status) -> None:
    if status:
        messagebox.showinfo("Activated", status.message)
        root.destroy()
    else:
        messagebox.showerror("Rejected", f"{status.message}\n(reason: {status.reason})")


root = tk.Tk()
root.title("Activate MyGuiApp")
tk.Label(root, text="Paste your license token, or pick your license.lic:").pack(padx=12, pady=8)
paste_box = tk.Text(root, height=6, width=64)
paste_box.pack(padx=12)
frame = tk.Frame(root)
frame.pack(pady=8)
tk.Button(frame, text="Activate pasted token", command=on_paste).pack(side="left", padx=4)
tk.Button(frame, text="Pick license.lic…", command=on_pick_file).pack(side="left", padx=4)
root.mainloop()
