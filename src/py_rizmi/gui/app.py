"""Main application window — Sidebar navigation with PyQt6."""
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QLabel, QPushButton, QStackedWidget, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from .theme import Color, get_base_stylesheet

from .views.hwid_view import HWIDTab as HWIDView
from .views.keymanager_view import KeyManagerTab as KeyManagerView
from .views.generate_view import GenerateTab as GenerateView
from .views.viewer_view import ViewerTab as ViewerView
from .views.guide_view import GuideView

LOGO_PATH = Path(__file__).resolve().parent.parent.parent / "media" / "logo.png"


class LicenseToolApp(QMainWindow):
    """Root window for py-Rizmi Licensing."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("py-Rizmi Licensing")
        self.resize(900, 700)
        self.setMinimumSize(800, 600)
        
        self.setStyleSheet(get_base_stylesheet())

        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self._build_sidebar()
        
        # Stacked Widget for Views
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack, stretch=1)
        
        self._build_views()

        self.select_view("hwid")
        self.status("Ready")

    def status(self, message: str, kind: str = "info") -> None:
        """Update the status bar with a message and colour."""
        color_map = {
            "info": Color.FG_MUTED,
            "success": Color.SUCCESS,
            "error": Color.ERROR,
            "warning": Color.WARNING,
        }
        color = color_map.get(kind, Color.FG_MUTED)
        self._status_label.setStyleSheet(f"color: {color};")
        self._status_label.setText(message)

    def _build_sidebar(self) -> None:
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setFixedWidth(220)
        self.sidebar_frame.setStyleSheet(f"background-color: {Color.SIDEBAR_BG}; border-right: 1px solid {Color.BORDER};")
        
        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(15, 30, 15, 20)
        sidebar_layout.setSpacing(5)
        
        self.main_layout.addWidget(self.sidebar_frame)

        # Logo
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if LOGO_PATH.exists():
            pixmap = QPixmap(str(LOGO_PATH))
            scaled_pixmap = pixmap.scaled(160, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(scaled_pixmap)
        else:
            self.logo_label.setText("py-Rizmi")
            font = self.logo_label.font()
            font.setPointSize(18)
            font.setBold(True)
            self.logo_label.setFont(font)
        
        sidebar_layout.addWidget(self.logo_label)
        sidebar_layout.addSpacing(30)

        # Nav Buttons
        self.nav_buttons: dict[str, QPushButton] = {}

        def add_nav(key: str, text: str) -> None:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedHeight(40)
            btn.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding-left: 15px;
                    border: none;
                    border-radius: 6px;
                    background-color: transparent;
                    color: {Color.TEXT};
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: {Color.SIDEBAR_HOVER};
                }}
                QPushButton:checked {{
                    background-color: {Color.SIDEBAR_HOVER};
                    color: {Color.ACCENT};
                    font-weight: bold;
                }}
            """)
            btn.clicked.connect(lambda _, k=key: self.select_view(k))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[key] = btn

        add_nav("hwid", "  Machine ID")
        add_nav("keys", "  Key Management")
        add_nav("gen", "  License Generation")
        add_nav("view", "  License Viewer")
        add_nav("guide", "  Integration Guide")

        sidebar_layout.addStretch()

        # Status
        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet(f"color: {Color.FG_MUTED}; font-size: 12px;")
        sidebar_layout.addWidget(self._status_label)

    def _build_views(self) -> None:
        self.views: dict[str, QWidget] = {}

        # Initialize views and pass `self` as the app reference.
        self.views["hwid"] = HWIDView(self)
        self.views["keys"] = KeyManagerView(self)
        self.views["gen"] = GenerateView(self.views["hwid"].get_hwid, self)  # type: ignore[attr-defined]
        self.views["view"] = ViewerView(self)
        self.views["guide"] = GuideView(self)

        for key, view in self.views.items():
            # Wrap in a container for padding
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(30, 30, 30, 30)
            container_layout.addWidget(view)
            self.stack.addWidget(container)
            
            # Store the container index as a property on the view or map it manually
            # But we can just use the index of addition
            
    def select_view(self, name: str) -> None:
        # Update button states
        for key, btn in self.nav_buttons.items():
            btn.setChecked(key == name)
            
        # Update stacked widget
        # The indices match the order we added them
        index_map = ["hwid", "keys", "gen", "view", "guide"]
        if name in index_map:
            idx = index_map.index(name)
            self.stack.setCurrentIndex(idx)
