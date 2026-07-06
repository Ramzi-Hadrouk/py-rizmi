"""Shared theme constants and style configuration for the GUI."""

# ---------- color palette ----------
class Color:
    BG = "#f5f5f5"
    FG = "#1a1a1a"
    ACCENT = "#2563eb"       # blue-600
    ACCENT_LIGHT = "#dbeafe" # blue-100
    SUCCESS = "#16a34a"      # green-600
    SUCCESS_LIGHT = "#dcfce7"
    ERROR = "#dc2626"        # red-600
    ERROR_LIGHT = "#fee2e2"
    WARNING = "#d97706"      # amber-600
    WARNING_LIGHT = "#fef3c7"
    DISABLED = "#9ca3af"
    BORDER = "#d1d5db"
    WHITE = "#ffffff"

# ---------- font sizes ----------
class Font:
    H1 = ("TkDefaultFont", 14, "bold")
    H2 = ("TkDefaultFont", 12, "bold")
    BODY = ("TkDefaultFont", 10)
    SMALL = ("TkDefaultFont", 9)
    MONO = ("Consolas", 10)
    MONO_SMALL = ("Consolas", 9)

# ---------- padding ----------
class Pad:
    XS = 2
    SM = 4
    MD = 8
    LG = 12
    XL = 16
    XXL = 24


import customtkinter as ctk
import os
from pathlib import Path

def configure_ctk_styles() -> None:
    """Apply custom CTk styles and theme."""
    ctk.set_appearance_mode("Light")
    theme_path = Path(__file__).resolve().parent / "custom_theme.json"
    if theme_path.exists():
        ctk.set_default_color_theme(str(theme_path))
    else:
        ctk.set_default_color_theme("blue")
