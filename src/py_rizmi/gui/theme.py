"""Centralized styling and theming for PyQt6."""
from __future__ import annotations

from typing import TYPE_CHECKING

import qdarktheme

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QApplication

class Color:
    """Color palette matching the light modern design."""
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
    """Apply the custom qdarktheme with our accent colors."""
    qdarktheme.setup_theme(
        theme="light",
        custom_colors={
            "[light]": {
                "primary": Color.ACCENT,
            },
        },
        corner_shape="rounded",
    )

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
