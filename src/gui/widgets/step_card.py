"""Reusable StepCard widget — numbered card with accent left stripe."""
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt

class StepCard(QFrame):
    """A card with a colored left-accent stripe, step number, title, divider,
    and a public `body_layout` where callers place their content."""

    def __init__(self, step: int, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("StepCardBody")
        
        # Main layout for the card
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Background frame to apply styling properly
        bg_frame = QFrame()
        bg_frame.setStyleSheet("background-color: #1f2937; border-radius: 10px;") # gray-800
        bg_layout = QHBoxLayout(bg_frame)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        bg_layout.setSpacing(0)
        self.main_layout.addWidget(bg_frame)

        # ── Left accent stripe ─────────────────────────────────────────
        accent = QFrame()
        accent.setObjectName("StepCardAccent")
        accent.setFixedWidth(4)
        bg_layout.addWidget(accent)

        # ── Inner wrapper ──────────────────────────────────────────────
        inner = QFrame()
        inner.setObjectName("StepCardInner")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(16, 14, 16, 16)
        inner_layout.setSpacing(10)
        bg_layout.addWidget(inner)

        # ── Header row ─────────────────────────────────────────────────
        hdr = QWidget()
        hdr_layout = QHBoxLayout(hdr)
        hdr_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_step = QLabel(f"STEP {step}")
        lbl_step.setObjectName("StepNumber")
        hdr_layout.addWidget(lbl_step)
        
        lbl_title = QLabel(f"  —  {title}")
        lbl_title.setObjectName("StepTitle")
        hdr_layout.addWidget(lbl_title)
        hdr_layout.addStretch()
        
        inner_layout.addWidget(hdr)

        # ── Divider ────────────────────────────────────────────────────
        divider = QFrame()
        divider.setObjectName("StepDivider")
        divider.setFixedHeight(1)
        inner_layout.addWidget(divider)

        # ── Public body ─────────────────────────────────────────────────
        self.body_widget = QWidget()
        self.body_layout = QVBoxLayout(self.body_widget)
        self.body_layout.setContentsMargins(0, 6, 0, 0)
        self.body_layout.setSpacing(10)
        inner_layout.addWidget(self.body_widget)
