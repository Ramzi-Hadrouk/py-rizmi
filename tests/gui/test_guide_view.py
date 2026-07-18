import pytest
from pathlib import Path
from unittest.mock import patch

from pytestqt.qtbot import QtBot
from py_rizmi.gui.views.guide_view import GuideView


def test_guide_view_loads_readme(qtbot: QtBot) -> None:
    """Test that GuideView successfully loads README.md from the project root."""
    view = GuideView()
    qtbot.addWidget(view)
    
    html = view.browser.toHtml()
    assert "Guide not found" not in html
    assert "Offline RSA-signed license management" in html or "py-Rizmi" in html or "Rizmi" in html


def test_guide_view_not_found(qtbot: QtBot) -> None:
    """Test fallback when README.md is not found."""
    with patch("importlib.resources.files", side_effect=Exception("Module not found")):
        with patch.object(Path, "exists", return_value=False):
            view = GuideView()
            qtbot.addWidget(view)
            
            html = view.browser.toHtml()
            assert "Guide not found" in html
