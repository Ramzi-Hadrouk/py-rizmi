"""Main application window — four-tab notebook with themed UI."""
import tkinter as tk
from tkinter import ttk
from pathlib import Path

from PIL import Image, ImageTk

from .theme import Color, Font, Pad, configure_ttk_styles
from .tabs.hwid_tab import HWIDTab
from .tabs.keymanager_tab import KeyManagerTab
from .tabs.generate_tab import GenerateTab
from .tabs.viewer_tab import ViewerTab

LOGO_PATH = Path(__file__).resolve().parent.parent.parent / "media" / "logo.png"


class LicenseToolApp(tk.Tk):
    """Root window for py-Rizmi Licensing."""

    def __init__(self):
        super().__init__()
        self.title("py-Rizmi Licensing")
        self.geometry("820x760")
        self.minsize(720, 640)
        self.configure(bg=Color.BG)

        self._configure_styles()
        self._set_icon()
        self._build_logo()
        self._build_tabs()
        self._build_status_bar()

        self.status("Ready")

    # ---------- helpers ----------

    def status(self, message: str, kind: str = "info") -> None:
        """Update the status bar with a message and colour."""
        color_map = {
            "info": Color.FG,
            "success": Color.SUCCESS,
            "error": Color.ERROR,
            "warning": Color.WARNING,
        }
        self._status_var.set(message)
        self._status_label.config(foreground=color_map.get(kind, Color.FG))

    # ---------- private ----------

    def _set_icon(self) -> None:
        try:
            img = Image.open(LOGO_PATH)
            self.iconphoto(True, ImageTk.PhotoImage(img))
        except Exception:
            pass

    def _configure_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        configure_ttk_styles(style)

    def _build_logo(self) -> None:
        try:
            img = Image.open(LOGO_PATH)
            base_width = 200
            w_percent = base_width / float(img.size[0])
            h_size = int(float(img.size[1]) * w_percent)
            img = img.resize((base_width, h_size), Image.Resampling.LANCZOS)
            self._logo_img = ImageTk.PhotoImage(img)
            tk.Label(self, image=self._logo_img, bg=Color.BG,
                     bd=0).pack(pady=(Pad.LG, 0))
        except Exception:
            pass

    def _build_tabs(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=Pad.MD, pady=Pad.MD)

        self.hwid_tab = HWIDTab(notebook, app=self)
        self.keymanager_tab = KeyManagerTab(notebook, app=self)
        self.generate_tab = GenerateTab(
            notebook,
            get_hwid_cb=self.hwid_tab.get_hwid,
            app=self,
        )
        self.viewer_tab = ViewerTab(notebook, app=self)

        notebook.add(self.hwid_tab, text="  1.  Machine ID  ")
        notebook.add(self.keymanager_tab, text="  2.  Key Management  ")
        notebook.add(self.generate_tab, text="  3.  License Generation  ")
        notebook.add(self.viewer_tab, text="  4.  License Viewer  ")

    def _build_status_bar(self) -> None:
        frame = ttk.Frame(self, style="Status.TLabel")
        frame.pack(fill="x", side="bottom")
        self._status_var = tk.StringVar()
        self._status_label = ttk.Label(
            frame, textvariable=self._status_var, style="Status.TLabel"
        )
        self._status_label.pack(fill="x")
