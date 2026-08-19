"""Main application window — Sidebar navigation with PyQt6."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QMessageBox, QApplication,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QKeySequence, QShortcut, QAction, QIcon

from .theme import Color, get_base_stylesheet

from .views.hwid_view import HWIDTab as HWIDView
from .views.keymanager_view import KeyManagerTab as KeyManagerView
from .views.generate_view import GenerateTab as GenerateView
from .views.viewer_view import ViewerTab as ViewerView
from .views.swap_view import LicenseSwapTab as SwapView
from .views.guide_view import GuideView




def _resolve_logo_path() -> Optional[Path]:
    """Find logo.png across source, install, and CWD layouts (cross-platform)."""
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "media" / "logo.png",  # repo root /media (dev)
        here.parents[2] / "media" / "logo.png",  # src/media
        Path.cwd() / "media" / "logo.png",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


LOGO_PATH = _resolve_logo_path()


class LicenseToolApp(QMainWindow):
    """Root window for py-Rizmi Licensing."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("py-Rizmi Licensing")
        self.resize(960, 720)
        self.setMinimumSize(800, 600)

        self.setStyleSheet(get_base_stylesheet())

        if LOGO_PATH is not None:
            self.setWindowIcon(QIcon(str(LOGO_PATH)))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self._build_menu()
        self._build_sidebar()

        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack, stretch=1)

        self._build_views()
        self._build_status_bar()
        self._build_shortcuts()

        self.select_view("hwid")
        self.status("Ready")

    def status(self, message: str, kind: str = "info") -> None:
        """Update status bar (and sidebar mirror) with a coloured message."""
        color_map = {
            "info": Color.FG_MUTED,
            "success": Color.SUCCESS,
            "error": Color.ERROR,
            "warning": Color.WARNING,
        }
        color = color_map.get(kind, Color.FG_MUTED)
        self._status_label.setStyleSheet(f"color: {color}; font-size: 12px;")
        self._status_label.setText(message)
        if hasattr(self, "_status_bar_label"):
            self._status_bar_label.setStyleSheet(f"color: {color};")
            self._status_bar_label.setText(f"  {message}")

    def _build_menu(self) -> None:
        menubar = self.menuBar()
        assert menubar is not None

        file_menu = menubar.addMenu("&File")
        assert file_menu is not None
        quit_action = QAction("E&xit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        app = QApplication.instance()
        if app is not None:
            quit_action.triggered.connect(app.quit)
        file_menu.addAction(quit_action)

        view_menu = menubar.addMenu("&View")
        assert view_menu is not None
        nav_items = [
            ("Machine ID", "hwid", "Ctrl+1"),
            ("Key Management", "keys", "Ctrl+2"),
            ("License Generation", "gen", "Ctrl+3"),
            ("License Viewer", "view", "Ctrl+4"),
            ("License Swap", "swap", "Ctrl+5"),
            ("Integration Guide", "guide", "Ctrl+6"),
        ]
        for label, key, shortcut in nav_items:
            action = QAction(label, self)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(lambda _checked=False, k=key: self.select_view(k))
            view_menu.addAction(action)

        help_menu = menubar.addMenu("&Help")
        assert help_menu is not None
        guide_action = QAction("Integration &Guide", self)
        guide_action.setShortcut(QKeySequence("F1"))
        guide_action.triggered.connect(lambda: self.select_view("guide"))
        help_menu.addAction(guide_action)
        about_action = QAction("&About py-Rizmi", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About py-Rizmi",
            "<b>py-Rizmi Licensing</b><br><br>"
            "Desktop toolkit for machine IDs, RSA keypairs, "
            "and signed license issuance.<br><br>"
            "Use View menu or Ctrl+1–5 to switch panels.",
        )

    def _build_status_bar(self) -> None:
        sb = self.statusBar()
        assert sb is not None
        self._status_bar_label = QLabel("  Ready")
        self._status_bar_label.setStyleSheet(f"color: {Color.FG_MUTED};")
        sb.addWidget(self._status_bar_label, stretch=1)

    def _build_shortcuts(self) -> None:
        shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        shortcut.activated.connect(self.close)

    def _build_sidebar(self) -> None:
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setFixedWidth(220)
        self.sidebar_frame.setStyleSheet(
            f"background-color: {Color.SIDEBAR_BG}; "
            f"border-right: 1px solid {Color.BORDER};"
        )

        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(15, 24, 15, 16)
        sidebar_layout.setSpacing(4)

        self.main_layout.addWidget(self.sidebar_frame)

        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setAccessibleName("py-Rizmi logo")
        if LOGO_PATH is not None:
            pixmap = QPixmap(str(LOGO_PATH))
            scaled = pixmap.scaled(
                140, 140,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.logo_label.setPixmap(scaled)
        else:
            self.logo_label.setText("py-Rizmi")
            font = self.logo_label.font()
            font.setPointSize(18)
            font.setBold(True)
            self.logo_label.setFont(font)

        sidebar_layout.addWidget(self.logo_label)
        sidebar_layout.addSpacing(20)

        self.nav_buttons: dict[str, QPushButton] = {}

        def add_nav(key: str, text: str) -> None:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedHeight(40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setAccessibleName(text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding-left: 12px;
                    border: none;
                    border-radius: 6px;
                    background-color: transparent;
                    color: {Color.TEXT};
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: {Color.SIDEBAR_HOVER};
                }}
                QPushButton:checked {{
                    background-color: {Color.SIDEBAR_HOVER};
                    color: {Color.ACCENT};
                    font-weight: bold;
                }}
                QPushButton:focus {{
                    border: 2px solid {Color.ACCENT};
                }}
            """)
            btn.clicked.connect(lambda _, k=key: self.select_view(k))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[key] = btn

        add_nav("hwid", "Machine ID")
        add_nav("keys", "Key Management")
        add_nav("gen", "License Generation")
        add_nav("view", "License Viewer")
        add_nav("swap", "License Swap")
        add_nav("guide", "Integration Guide")

        sidebar_layout.addStretch()

        # Compact sidebar mirror of status (optional glance while focused on nav)
        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet(f"color: {Color.FG_MUTED}; font-size: 12px;")
        sidebar_layout.addWidget(self._status_label)

    def _build_views(self) -> None:
        self.views: dict[str, QWidget] = {}

        self.views["hwid"] = HWIDView(self)
        self.views["keys"] = KeyManagerView(self)
        self.views["gen"] = GenerateView(self.views["hwid"].get_hwid, self)  # type: ignore[attr-defined]
        self.views["view"] = ViewerView(self)
        self.views["swap"] = SwapView(self)
        self.views["guide"] = GuideView(self)

        for _key, view in self.views.items():
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(24, 24, 24, 24)
            container_layout.addWidget(view)
            self.stack.addWidget(container)

    def select_view(self, name: str) -> None:
        for key, btn in self.nav_buttons.items():
            btn.setChecked(key == name)

        index_map = ["hwid", "keys", "gen", "view", "swap", "guide"]
        if name in index_map:
            self.stack.setCurrentIndex(index_map.index(name))


    def use_signing_key(
        self,
        *,
        path: str | None = None,
        pem: str | None = None,
        passphrase: str | None = None,
    ) -> None:
        """Handoff from Key Management into License Generation."""
        gen = self.views.get("gen")
        if isinstance(gen, GenerateView):
            gen.set_signing_key(path=path, pem=pem, passphrase=passphrase)
        self.select_view("gen")
        self.status("Signing key ready for license generation", "success")
