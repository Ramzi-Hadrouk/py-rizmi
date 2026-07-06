"""Main application window — Sidebar navigation with modern CustomTkinter UI."""
import customtkinter as ctk
from pathlib import Path
from PIL import Image

from .theme import Color, configure_ctk_styles
from .views.hwid_view import HWIDTab as HWIDView
from .views.keymanager_view import KeyManagerTab as KeyManagerView
from .views.generate_view import GenerateTab as GenerateView
from .views.viewer_view import ViewerTab as ViewerView
from .views.guide_view import GuideView

LOGO_PATH = Path(__file__).resolve().parent.parent.parent / "media" / "logo.png"

class LicenseToolApp(ctk.CTk):
    """Root window for py-Rizmi Licensing."""

    def __init__(self):
        super().__init__()
        self.title("py-Rizmi Licensing")
        self.geometry("900x700")
        self.minsize(800, 600)

        configure_ctk_styles()
        
        # Grid Layout: 1 row, 2 columns
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_views()

        self.select_view("hwid")
        self.status("Ready")

    def status(self, message: str, kind: str = "info") -> None:
        """Update the status bar with a message and colour."""
        color_map = {
            "info": Color.FG,
            "success": Color.SUCCESS,
            "error": Color.ERROR,
            "warning": Color.WARNING,
        }
        self._status_label.configure(text=message, text_color=color_map.get(kind, Color.FG))

    def _build_sidebar(self) -> None:
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=("gray95", "gray10"))
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        # Logo - Fixed Aspect Ratio
        try:
            img = Image.open(LOGO_PATH)
            w, h = img.size
            target_w = 160
            target_h = int(target_w * (h / w))
            self._logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(target_w, target_h))
            self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="", image=self._logo_img)
            self.logo_label.grid(row=0, column=0, padx=20, pady=(40, 40))
        except Exception:
            self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="py-Rizmi", font=ctk.CTkFont(size=24, weight="bold"))
            self.logo_label.grid(row=0, column=0, padx=20, pady=(40, 40))

        # Nav Buttons (Modern styling)
        nav_kwargs = {
            "fg_color": "transparent",
            "text_color": ("gray10", "gray90"),
            "hover_color": ("gray85", "gray20"),
            "anchor": "w",
            "font": ctk.CTkFont(size=14),
            "height": 40
        }

        self.nav_hwid = ctk.CTkButton(self.sidebar_frame, text="  Machine ID", command=lambda: self.select_view("hwid"), **nav_kwargs)
        self.nav_hwid.grid(row=1, column=0, padx=15, pady=5, sticky="ew")

        self.nav_keys = ctk.CTkButton(self.sidebar_frame, text="  Key Management", command=lambda: self.select_view("keys"), **nav_kwargs)
        self.nav_keys.grid(row=2, column=0, padx=15, pady=5, sticky="ew")

        self.nav_gen = ctk.CTkButton(self.sidebar_frame, text="  License Generation", command=lambda: self.select_view("gen"), **nav_kwargs)
        self.nav_gen.grid(row=3, column=0, padx=15, pady=5, sticky="ew")

        self.nav_view = ctk.CTkButton(self.sidebar_frame, text="  License Viewer", command=lambda: self.select_view("view"), **nav_kwargs)
        self.nav_view.grid(row=4, column=0, padx=15, pady=5, sticky="ew")

        self.nav_guide = ctk.CTkButton(self.sidebar_frame, text="  Integration Guide", command=lambda: self.select_view("guide"), **nav_kwargs)
        self.nav_guide.grid(row=5, column=0, padx=15, pady=5, sticky="ew")

        # Status
        self._status_label = ctk.CTkLabel(self.sidebar_frame, text="", font=ctk.CTkFont(size=12), text_color="gray50")
        self._status_label.grid(row=7, column=0, padx=20, pady=20, sticky="sw")

    def _build_views(self) -> None:
        self.views = {}
        
        self.views["hwid"] = HWIDView(self, app=self)
        self.views["keys"] = KeyManagerView(self, app=self)
        self.views["gen"] = GenerateView(self, get_hwid_cb=self.views["hwid"].get_hwid, app=self)
        self.views["view"] = ViewerView(self, app=self)
        self.views["guide"] = GuideView(self, app=self)

        for view in self.views.values():
            view.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)

    def select_view(self, name: str):
        # Update button colors and view visibility
        for btn_name, btn in [("hwid", self.nav_hwid), ("keys", self.nav_keys), ("gen", self.nav_gen), ("view", self.nav_view), ("guide", self.nav_guide)]:
            if name == btn_name:
                btn.configure(fg_color=("gray85", "gray25"))
                self.views[btn_name].grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
            else:
                btn.configure(fg_color="transparent")
                if btn_name in self.views:
                    self.views[btn_name].grid_remove()
