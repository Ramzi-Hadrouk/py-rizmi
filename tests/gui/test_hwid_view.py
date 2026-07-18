import pytest
from PyQt6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot
from unittest.mock import patch

from py_rizmi.gui.views.hwid_view import HWIDTab


def test_hwid_view_generate_and_copy(qtbot: QtBot) -> None:
    """Test HWIDTab generates HWID and copies to clipboard."""
    view = HWIDTab()
    qtbot.addWidget(view)
    
    with patch("py_rizmi.core.hwid.HardwareIdentifier.get_machine_id", return_value="dummy_hwid_123"):
        view._on_generate()
        
    assert view.hwid_entry.text() == "dummy_hwid_123"
    
    view._on_copy()
    assert "Copied" in view._status_label.text()
    
    cb = QApplication.clipboard()
    assert cb is not None
    assert cb.text() == "dummy_hwid_123"


def test_hwid_view_auto_copy(qtbot: QtBot) -> None:
    """Test auto-copy functionality."""
    view = HWIDTab()
    qtbot.addWidget(view)
    
    view.chk_auto.setChecked(True)
    
    with patch("py_rizmi.core.hwid.HardwareIdentifier.get_machine_id", return_value="auto_hwid_456"):
        view._on_generate()
        
    assert view.hwid_entry.text() == "auto_hwid_456"
    assert "Copied" in view._status_label.text()
    
    cb = QApplication.clipboard()
    assert cb is not None
    assert cb.text() == "auto_hwid_456"
