"""Unit tests for License Generation and related UX fixes."""
from unittest.mock import patch

from PyQt6.QtWidgets import QMessageBox
from pytestqt.qtbot import QtBot

from py_rizmi.gui.views.generate_view import GenerateTab


def test_generate_view_valid_payload(qtbot: QtBot) -> None:
    """Test generating a payload with valid inputs."""
    view = GenerateTab()
    qtbot.addWidget(view)

    view.entry_client.setText("Test Client")
    view.entry_license_id.setText("LIC-123")
    view.entry_hwid.setText("dummy-hwid")
    view.entry_max_clients.setText("50")
    view.entry_grace_days.setText("7")

    payload = view._build_payload()

    assert payload is not None
    assert payload.client == "Test Client"
    assert payload.license_id == "LIC-123"
    assert payload.hwid == "dummy-hwid"
    assert payload.max_clients == 50
    assert payload.grace_days == 7


def test_generate_view_missing_fields_shows_error(qtbot: QtBot) -> None:
    """Test missing required fields shows an error."""
    view = GenerateTab()
    qtbot.addWidget(view)

    with patch.object(QMessageBox, "critical") as mock_crit:
        payload = view._build_payload()

    assert payload is None
    mock_crit.assert_called_once()
    assert "required fields" in mock_crit.call_args[0][2]


def test_generate_view_invalid_integer_shows_error(qtbot: QtBot) -> None:
    """Test that invalid integers in numeric fields show an error."""
    view = GenerateTab()
    qtbot.addWidget(view)

    view.entry_client.setText("Test Client")
    view.entry_license_id.setText("LIC-123")
    view.entry_hwid.setText("dummy-hwid")

    view.entry_max_clients.setText("abc")
    view.entry_grace_days.setText("14")

    with patch.object(QMessageBox, "critical") as mock_crit:
        payload = view._build_payload()

    assert payload is None
    mock_crit.assert_called_once()
    assert "Max Clients must be a valid integer" in mock_crit.call_args[0][2]

    view.entry_max_clients.setText("10")
    view.entry_grace_days.setText("xyz")

    with patch.object(QMessageBox, "critical") as mock_crit:
        payload = view._build_payload()

    assert payload is None
    mock_crit.assert_called_once()
    assert "Grace Days must be a valid integer" in mock_crit.call_args[0][2]


def test_issued_at_has_no_days_field(qtbot: QtBot) -> None:
    """Issued At must not show a days spinner (only Expires At does)."""
    view = GenerateTab()
    qtbot.addWidget(view)
    assert view.iat_days is None
    assert view.exp_days is not None


def test_online_mode_requires_server_url(qtbot: QtBot) -> None:
    """Online mode without Server URL must fail validation."""
    view = GenerateTab()
    qtbot.addWidget(view)

    view.entry_client.setText("Test Client")
    view.entry_license_id.setText("LIC-123")
    view.entry_hwid.setText("dummy-hwid")
    view.combo_mode.setCurrentText("online")
    view.entry_server_url.clear()

    with patch.object(QMessageBox, "critical") as mock_crit:
        payload = view._build_payload()

    assert payload is None
    mock_crit.assert_called_once()
    assert "Server URL" in mock_crit.call_args[0][2]


def test_hwid_button_label_not_tab(qtbot: QtBot) -> None:
    """HWID pull action must not refer to obsolete 'Tab' navigation."""
    from PyQt6.QtWidgets import QPushButton

    view = GenerateTab()
    qtbot.addWidget(view)
    texts = [b.text() for b in view.findChildren(QPushButton)]
    assert any("Machine ID" in t for t in texts)
    assert not any("Tab" in t for t in texts)
