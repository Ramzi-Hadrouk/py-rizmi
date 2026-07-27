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
    FG_MUTED = "#6b7280"       # gray-500
    PANEL_BG = "#f3f4f6"       # gray-100
    BORDER = "#e5e7eb"         # gray-200
    SIDEBAR_BG = "#f9fafb"     # gray-50
    SIDEBAR_HOVER = "#e5e7eb"  # gray-200
    TEXT = "#111827"           # gray-900


def apply_theme(app: QApplication) -> None:
    """Apply a clean light theme using Qt's built-in Fusion style + QSS.

    No third-party theme library required.
    """
    from PyQt6.QtWidgets import QStyleFactory
    from PyQt6.QtGui import QPalette, QColor

    app.setStyle(QStyleFactory.create("Fusion"))

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor("#f9fafb"))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor("#111827"))
    palette.setColor(QPalette.ColorRole.Base,            QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor("#f3f4f6"))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor("#111827"))
    palette.setColor(QPalette.ColorRole.Text,            QColor("#111827"))
    palette.setColor(QPalette.ColorRole.Button,          QColor("#f3f4f6"))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor("#111827"))
    palette.setColor(QPalette.ColorRole.BrightText,      QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor("#2563eb"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Link,            QColor("#2563eb"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#9ca3af"))
    app.setPalette(palette)

    app.setStyleSheet("""
        QToolTip {
            background-color: #ffffff;
            color: #111827;
            border: 1px solid #e5e7eb;
            padding: 4px 8px;
            border-radius: 4px;
        }
        QScrollBar:vertical {
            background: #f3f4f6;
            width: 8px;
            margin: 0;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background: #d1d5db;
            border-radius: 4px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background: #9ca3af;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar:horizontal {
            background: #f3f4f6;
            height: 8px;
            margin: 0;
            border-radius: 4px;
        }
        QScrollBar::handle:horizontal {
            background: #d1d5db;
            border-radius: 4px;
            min-width: 20px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #9ca3af;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
        QPushButton {
            background-color: #f3f4f6;
            color: #111827;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            padding: 6px 14px;
        }
        QPushButton:hover {
            background-color: #e5e7eb;
        }
        QPushButton:pressed {
            background-color: #d1d5db;
        }
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #ffffff;
            color: #111827;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            padding: 4px 8px;
        }
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border: 1px solid #2563eb;
        }
        QComboBox {
            background-color: #ffffff;
            color: #111827;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            padding: 4px 8px;
        }
        QGroupBox {
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            margin-top: 8px;
            padding-top: 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            color: #6b7280;
        }
    """)

def get_base_stylesheet() -> str:
    """Returns extra QSS for specific custom widgets not covered by qdarktheme."""
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
    """
