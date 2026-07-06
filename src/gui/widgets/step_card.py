"""Reusable StepCard widget — numbered card with accent left stripe."""
import customtkinter as ctk
from ..theme import Color


class StepCard(ctk.CTkFrame):
    """A card with a colored left-accent stripe, step number, title, divider,
    and a public `body` frame where callers place their content."""

    def __init__(self, parent, step: int, title: str, **kwargs):
        kwargs.setdefault("fg_color", ("gray95", "gray13"))
        kwargs.setdefault("corner_radius", 10)
        super().__init__(parent, **kwargs)

        # ── Left accent stripe ─────────────────────────────────────────
        ctk.CTkFrame(
            self, width=4, fg_color=Color.ACCENT, corner_radius=0
        ).pack(side="left", fill="y")

        # ── Inner wrapper ──────────────────────────────────────────────
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(side="left", fill="both", expand=True)

        # ── Header row ─────────────────────────────────────────────────
        hdr = ctk.CTkFrame(inner, fg_color="transparent")
        hdr.pack(fill="x", padx=(12, 16), pady=(14, 0))

        ctk.CTkLabel(
            hdr,
            text=f"STEP {step}",
            text_color=Color.ACCENT,
            font=ctk.CTkFont(size=10, weight="bold"),
        ).pack(side="left")

        ctk.CTkLabel(
            hdr,
            text=f"  —  {title}",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left")

        # ── Divider ────────────────────────────────────────────────────
        ctk.CTkFrame(
            inner, height=1, fg_color=("gray80", "gray30")
        ).pack(fill="x", padx=(12, 16), pady=(8, 0))

        # ── Public body ─────────────────────────────────────────────────
        self.body = ctk.CTkFrame(inner, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=(12, 16), pady=(10, 16))
