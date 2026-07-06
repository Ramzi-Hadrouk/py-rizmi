"""Main application window — three-tab notebook."""
import tkinter as tk
from tkinter import ttk

from .tabs.hwid_tab import HWIDTab
from .tabs.generate_tab import GenerateTab
from .tabs.viewer_tab import ViewerTab


class LicenseToolApp(tk.Tk):
    """Root window for the License Management Tool."""

    def __init__(self):
        super().__init__()
        self.title("License Management Tool")
        self.geometry("820x760")
        self.minsize(720, 640)

        self._style()
        self._build_tabs()

    def _style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

    def _build_tabs(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.hwid_tab = HWIDTab(notebook)
        self.generate_tab = GenerateTab(
            notebook,
            get_hwid_cb=self.hwid_tab.get_hwid,
        )
        self.viewer_tab = ViewerTab(notebook)

        notebook.add(self.hwid_tab, text="  1.  Machine ID  ")
        notebook.add(self.generate_tab, text="  2.  License Generation  ")
        notebook.add(self.viewer_tab, text="  3.  License Viewer  ")
