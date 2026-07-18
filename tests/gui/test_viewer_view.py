import pytest
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime, timezone, timedelta
from typing import cast

from PyQt6.QtWidgets import QApplication, QFormLayout, QLabel
from pytestqt.qtbot import QtBot

from py_rizmi.gui.views.viewer_view import ViewerTab
from py_rizmi.gui.theme import Color


def test_viewer_view_valid_license(qtbot: QtBot) -> None:
    """Test ViewerTab with a valid (not expired) license."""
    view = ViewerTab()
    qtbot.addWidget(view)
    
    view.pub_entry.setText("dummy_pub.pem")
    view.lic_entry.setText("dummy.lic")
    
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=10)
    
    mock_data = {
        "client": "Test Client",
        "exp": int(future.timestamp()),
        "iat": int(now.timestamp())
    }
    
    mock_validator = MagicMock()
    mock_validator.decode_token.return_value = mock_data
    
    with patch("py_rizmi.gui.views.viewer_view.LicenseValidator.from_file", return_value=mock_validator):
        with patch("builtins.open", mock_open(read_data="dummy.jwt.token")):
            view._on_view()
            
    assert "Decoded successfully" in view.lbl_status.text()
    
    # Check the expiry row label (last row in the form layout)
    item = view.form_layout.itemAt(view.form_layout.rowCount() - 1, QFormLayout.ItemRole.FieldRole)
    assert item is not None
    lbl_v = cast(QLabel, item.widget())
    assert Color.SUCCESS in lbl_v.styleSheet()
    assert "remaining" in lbl_v.text()


def test_viewer_view_expired_license(qtbot: QtBot) -> None:
    """Test ViewerTab with an expired license."""
    view = ViewerTab()
    qtbot.addWidget(view)
    
    view.pub_entry.setText("dummy_pub.pem")
    view.lic_entry.setText("dummy.lic")
    
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=10)
    
    mock_data = {
        "client": "Test Client",
        "exp": int(past.timestamp()),
        "iat": int((past - timedelta(days=5)).timestamp())
    }
    
    mock_validator = MagicMock()
    mock_validator.decode_token.return_value = mock_data
    
    with patch("py_rizmi.gui.views.viewer_view.LicenseValidator.from_file", return_value=mock_validator):
        with patch("builtins.open", mock_open(read_data="dummy.jwt.token")):
            view._on_view()
            
    assert "Decoded successfully" in view.lbl_status.text()
    
    item = view.form_layout.itemAt(view.form_layout.rowCount() - 1, QFormLayout.ItemRole.FieldRole)
    assert item is not None
    lbl_v = cast(QLabel, item.widget())
    assert Color.ERROR in lbl_v.styleSheet()
    assert "EXPIRED by" in lbl_v.text()


def test_viewer_view_missing_files(qtbot: QtBot) -> None:
    """Test ViewerTab when files are not selected."""
    view = ViewerTab()
    qtbot.addWidget(view)
    
    with patch("py_rizmi.gui.views.viewer_view.QMessageBox.warning") as mock_warn:
        view._on_view()
        mock_warn.assert_called_once()
        assert "Select both" in mock_warn.call_args[0][2]
