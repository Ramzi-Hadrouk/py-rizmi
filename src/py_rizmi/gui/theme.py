"""Centralized styling and theming for PyQt6."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QApplication


class Color:
    """Color palette for the light design."""
    ACCENT = "#2563eb"
    ACCENT_HOVER = "#1d4ed8"
    ACCENT_LIGHT = "#dbeafe"
    SUCCESS = "#16a34a"
    SUCCESS_LIGHT = "#dcfce7"
    ERROR = "#dc2626"
    ERROR_HOVER = "#991b1b"
    ERROR_LIGHT = "#fee2e2"
    WARNING = "#d97706"
    WARNING_HOVER = "#b45309"
    WARNING_LIGHT = "#fef3c7"

    # Light mode specific colors
    FG_MUTED = "#4b5563"       # gray-600 — readable at small sizes
    PANEL_BG = "#f3f4f6"       # gray-100
    BORDER = "#e5e7eb"         # gray-200
    SIDEBAR_BG = "#f9fafb"     # gray-50
    SIDEBAR_HOVER = "#e5e7eb"  # gray-200
    TEXT = "#111827"           # gray-900
    WHITE = "#ffffff"


class TypeScale:
    """Shared type sizes (px) for consistent hierarchy."""
    DISPLAY = "22px"
    TITLE = "15px"
    BODY = "13px"
    CAPTION = "12px"
    SMALL = "11px"


def input_stylesheet(*, error: bool = False) -> str:
    """Standard input style — use instead of per-widget one-offs."""
    border = Color.ERROR if error else Color.BORDER
    return (
        f"background-color: {Color.WHITE}; color: {Color.TEXT}; "
        f"padding: 4px 8px; border: 1px solid {border}; border-radius: 6px;"
    )


def mono_input_stylesheet(*, error: bool = False) -> str:
    return input_stylesheet(error=error) + " font-family: monospace; font-size: 13px;"


def button_stylesheet(kind: str = "secondary") -> str:
    """Shared button variants: primary | secondary | warning | danger | ghost."""
    if kind == "primary":
        return f"""
            QPushButton {{
                background-color: {Color.ACCENT};
                color: {Color.WHITE};
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{ background-color: {Color.ACCENT_HOVER}; }}
            QPushButton:pressed {{ background-color: {Color.ACCENT_HOVER}; }}
            QPushButton:disabled {{
                background-color: {Color.BORDER};
                color: {Color.FG_MUTED};
            }}
            QPushButton:focus {{ border: 2px solid {Color.ACCENT_HOVER}; }}
        """
    if kind == "warning":
        return f"""
            QPushButton {{
                background-color: {Color.WARNING};
                color: {Color.WHITE};
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{ background-color: {Color.WARNING_HOVER}; }}
            QPushButton:disabled {{
                background-color: {Color.BORDER};
                color: {Color.FG_MUTED};
            }}
            QPushButton:focus {{ border: 2px solid {Color.WARNING_HOVER}; }}
        """
    if kind == "danger":
        return f"""
            QPushButton {{
                background-color: {Color.ERROR};
                color: {Color.WHITE};
                border: none;
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{ background-color: {Color.ERROR_HOVER}; }}
            QPushButton:focus {{ border: 2px solid {Color.ERROR_HOVER}; }}
        """
    if kind == "ghost":
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {Color.TEXT};
                border: 1px solid {Color.BORDER};
                border-radius: 6px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{ background-color: {Color.SIDEBAR_HOVER}; }}
            QPushButton:focus {{ border: 2px solid {Color.ACCENT}; }}
        """
    # secondary (default)
    return f"""
        QPushButton {{
            background-color: {Color.PANEL_BG};
            color: {Color.TEXT};
            border: 1px solid {Color.BORDER};
            border-radius: 6px;
            padding: 6px 14px;
        }}
        QPushButton:hover {{ background-color: {Color.SIDEBAR_HOVER}; }}
        QPushButton:disabled {{
            color: {Color.FG_MUTED};
            background-color: {Color.PANEL_BG};
        }}
        QPushButton:focus {{ border: 2px solid {Color.ACCENT}; }}
    """


def apply_theme(app: QApplication) -> None:
    """Apply a clean light theme using Qt's built-in Fusion style + QSS.

    No third-party theme library required. Fusion renders consistently
    across Windows, macOS, and Linux.
    """
    from PyQt6.QtWidgets import QStyleFactory
    from PyQt6.QtGui import QPalette, QColor

    app.setStyle(QStyleFactory.create("Fusion"))

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(Color.SIDEBAR_BG))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(Color.TEXT))
    palette.setColor(QPalette.ColorRole.Base,            QColor(Color.WHITE))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(Color.PANEL_BG))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor(Color.WHITE))
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor(Color.TEXT))
    palette.setColor(QPalette.ColorRole.Text,            QColor(Color.TEXT))
    palette.setColor(QPalette.ColorRole.Button,          QColor(Color.PANEL_BG))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(Color.TEXT))
    palette.setColor(QPalette.ColorRole.BrightText,      QColor(Color.WHITE))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(Color.ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(Color.WHITE))
    palette.setColor(QPalette.ColorRole.Link,            QColor(Color.ACCENT))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#9ca3af"))
    app.setPalette(palette)

    app.setStyleSheet(f"""
        QToolTip {{
            background-color: {Color.WHITE};
            color: {Color.TEXT};
            border: 1px solid {Color.BORDER};
            padding: 4px 8px;
            border-radius: 4px;
        }}
        QScrollBar:vertical {{
            background: {Color.PANEL_BG};
            width: 8px;
            margin: 0;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: #d1d5db;
            border-radius: 4px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: #9ca3af;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar:horizontal {{
            background: {Color.PANEL_BG};
            height: 8px;
            margin: 0;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal {{
            background: #d1d5db;
            border-radius: 4px;
            min-width: 20px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: #9ca3af;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
        QPushButton {{
            background-color: {Color.PANEL_BG};
            color: {Color.TEXT};
            border: 1px solid {Color.BORDER};
            border-radius: 6px;
            padding: 6px 14px;
        }}
        QPushButton:hover {{
            background-color: {Color.SIDEBAR_HOVER};
        }}
        QPushButton:pressed {{
            background-color: #d1d5db;
        }}
        QPushButton:disabled {{
            color: {Color.FG_MUTED};
        }}
        QPushButton:focus {{
            border: 2px solid {Color.ACCENT};
        }}
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {Color.WHITE};
            color: {Color.TEXT};
            border: 1px solid {Color.BORDER};
            border-radius: 6px;
            padding: 4px 8px;
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 1px solid {Color.ACCENT};
        }}
        QComboBox {{
            background-color: {Color.WHITE};
            color: {Color.TEXT};
            border: 1px solid {Color.BORDER};
            border-radius: 6px;
            padding: 4px 8px;
        }}
        QComboBox:focus {{
            border: 1px solid {Color.ACCENT};
        }}
        QGroupBox {{
            border: 1px solid {Color.BORDER};
            border-radius: 6px;
            margin-top: 8px;
            padding-top: 8px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            color: {Color.FG_MUTED};
        }}
        QStatusBar {{
            background-color: {Color.SIDEBAR_BG};
            color: {Color.FG_MUTED};
            border-top: 1px solid {Color.BORDER};
        }}
        QMenuBar {{
            background-color: {Color.SIDEBAR_BG};
            color: {Color.TEXT};
            border-bottom: 1px solid {Color.BORDER};
        }}
        QMenuBar::item:selected {{
            background-color: {Color.SIDEBAR_HOVER};
        }}
        QMenu {{
            background-color: {Color.WHITE};
            border: 1px solid {Color.BORDER};
        }}
        QMenu::item:selected {{
            background-color: {Color.ACCENT_LIGHT};
            color: {Color.TEXT};
        }}
    """)


def get_base_stylesheet() -> str:
    """Extra QSS for custom widgets (StepCard, Panel) on top of Fusion theme."""
    return f"""
    /* StepCard */
    QFrame#StepCardBody {{
        background-color: transparent;
    }}
    QFrame#StepCardAccent {{
        background-color: {Color.ACCENT};
        border-top-left-radius: 10px;
        border-bottom-left-radius: 10px;
    }}
    QFrame#StepCardInner {{
        background-color: transparent;
    }}
    QLabel#StepNumber {{
        color: {Color.ACCENT};
        font-weight: bold;
        font-size: 11px;
    }}
    QLabel#StepTitle {{
        font-weight: bold;
        font-size: 15px;
    }}
    QFrame#StepDivider {{
        background-color: {Color.BORDER};
    }}

    /* Utility panels */
    QFrame#Panel {{
        background-color: {Color.PANEL_BG};
        border-radius: 8px;
    }}

    QLabel#PageTitle {{
        font-size: {TypeScale.DISPLAY};
        font-weight: bold;
        color: {Color.TEXT};
    }}
    QLabel#PageSubtitle {{
        font-size: {TypeScale.BODY};
        color: {Color.FG_MUTED};
    }}
    QLabel#EmptyState {{
        color: {Color.FG_MUTED};
        font-size: {TypeScale.BODY};
        padding: 24px;
    }}
    QLabel#VerifyBanner {{
        font-weight: bold;
        font-size: {TypeScale.BODY};
        padding: 10px 12px;
        border-radius: 6px;
    }}
    """
