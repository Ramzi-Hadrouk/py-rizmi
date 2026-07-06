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


def configure_ttk_styles(style: object) -> None:
    """Apply custom ttk styles for a polished look."""
    style.configure(".", font=Font.BODY, background=Color.BG)

    style.configure("TLabel", background=Color.BG, foreground=Color.FG)
    style.configure("TFrame", background=Color.BG)
    style.configure("TButton", padding=(Pad.MD, Pad.SM))
    style.configure("TLabelframe", background=Color.BG)
    style.configure("TLabelframe.Label", background=Color.BG,
                    foreground=Color.FG, font=Font.H2)

    # success / error variants
    style.configure("Success.TLabel", foreground=Color.SUCCESS,
                    font=Font.BODY)
    style.configure("Error.TLabel", foreground=Color.ERROR,
                    font=Font.BODY)
    style.configure("Warning.TLabel", foreground=Color.WARNING,
                    font=Font.BODY)

    # accent buttons
    style.configure("Accent.TButton", foreground=Color.ACCENT)
    style.configure("Success.TButton", foreground=Color.SUCCESS)
    style.configure("Danger.TButton", foreground=Color.ERROR)

    # heading label
    style.configure("Heading.TLabel", font=Font.H1, background=Color.BG)

    # status bar
    style.configure("Status.TLabel", font=Font.SMALL,
                    background=Color.BORDER, foreground=Color.FG,
                    padding=(Pad.MD, Pad.XS))
