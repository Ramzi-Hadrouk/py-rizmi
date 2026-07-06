"""Centralized styling and theming for PyQt6."""
import qdarktheme

class Color:
    """Color palette matching the dark modern design."""
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
    FG_MUTED = "#9ca3af"

def apply_theme(app) -> None:
    """Apply the custom qdarktheme with our accent colors."""
    qdarktheme.setup_theme(
        theme="dark",
        custom_colors={
            "[dark]": {
                "primary": Color.ACCENT,
            },
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
        background-color: #374151; /* gray-700 */
    }}
    
    /* Utility panels */
    QFrame#Panel {{
        background-color: #1f2937; /* gray-800 */
        border-radius: 8px;
    }}
    """
