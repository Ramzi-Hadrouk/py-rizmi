"""Trial status banner widget for PyQt6.

A compact, color-coded banner an integrated app (or this toolkit) can
pin above its main content to show trial/licensing state at a glance:
days remaining while active, a purchase prompt when expired.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from ..theme import Color


class TrialBanner(QFrame):
    """Color-coded trial/license status banner.

    Feed it a `core.trial.TrialStatus` via `update_status()`; it picks
    colors and copy accordingly. *on_buy* (optional) is invoked when the
    user clicks the purchase button shown in blocked states.
    """

    def __init__(
        self,
        on_buy: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._on_buy = on_buy
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedHeight(44)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)

        self.label = QLabel()
        self.label.setWordWrap(False)
        layout.addWidget(self.label, stretch=1)

        self.buy_button = QPushButton("Buy a License")
        self.buy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.buy_button.setStyleSheet(
            f"QPushButton {{ background-color: {Color.ACCENT}; color: white;"
            f" border: none; border-radius: 4px; padding: 4px 14px;"
            f" font-weight: bold; }}"
            f"QPushButton:hover {{ opacity: 0.9; }}"
        )
        self.buy_button.clicked.connect(self._handle_buy)
        self.buy_button.hide()
        layout.addWidget(self.buy_button)

        self.update_status(None)

    # ---- API -----------------------------------------------------------

    def update_status(self, status: Any) -> None:
        """Render a `py_rizmi.core.trial.TrialStatus` (or None)."""
        if status is None:
            self._render("dim", "Trial status unknown")
            return

        state = getattr(status, "state", "")
        days = getattr(status, "days_left", 0)
        detail = getattr(status, "detail", "")

        if state == "licensed":
            self._render("success", "✓ Licensed — thank you for your purchase")
        elif state == "trial_active":
            day_word = "day" if days == 1 else "days"
            style = "warning" if days <= 3 else "info"
            suffix = " — buy soon!" if days <= 3 else ""
            self._render(style, f"⏳ Trial: {days} {day_word} left{suffix}")
        elif state == "trial_expired":
            self._render("error", "✗ Trial expired — buy a license to keep using this app")
        elif state == "tampered":
            self._render("error", f"✗ Trial integrity check failed{': ' + detail if detail else ''}")
        elif state == "licensed_invalid":
            self._render("warning", f"⚠ License problem: {detail or 'validation failed'}")
        elif state == "no_trial":
            self._render("dim", "No license or trial found")
        else:
            self._render("error", f"✗ {detail or state}")

    # ---- internals -------------------------------------------------------

    def _handle_buy(self) -> None:
        if self._on_buy is not None:
            self._on_buy()

    def _render(self, kind: str, text: str) -> None:
        bg = {
            "success": Color.SUCCESS,
            "warning": Color.WARNING,
            "error": Color.ERROR,
            "info": Color.ACCENT,
            "dim": Color.FG_MUTED,
        }.get(kind, Color.FG_MUTED)
        self.setStyleSheet(
            f"QFrame {{ background-color: {bg}22;"  # ~13% alpha tint
            f" border: 1px solid {bg}; border-radius: 6px; }}"
            f" QLabel {{ color: {bg}; font-weight: bold; }}"
        )
        self.label.setText(text)
        show_buy = kind in ("error",) and ("expired" in text.lower() or "integrity" in text.lower())
        self.buy_button.setVisible(show_buy)
