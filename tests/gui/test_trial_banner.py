"""GUI tests for the TrialBanner widget."""
from dataclasses import dataclass

from py_rizmi.gui.widgets.trial_banner import TrialBanner


@dataclass
class FakeStatus:
    state: str
    days_left: int = 0
    detail: str = ""


def test_banner_active_trial_more_than_3_days(qtbot):
    banner = TrialBanner()
    qtbot.addWidget(banner)
    banner.update_status(FakeStatus(state="trial_active", days_left=10))
    assert "10 days left" in banner.label.text()
    assert not _button_shown(banner)


def test_banner_active_trial_low_days_shows_urgency(qtbot):
    banner = TrialBanner()
    qtbot.addWidget(banner)
    banner.update_status(FakeStatus(state="trial_active", days_left=2))
    assert "2 days left" in banner.label.text()
    assert "buy soon" in banner.label.text().lower()


def test_banner_singular_day(qtbot):
    banner = TrialBanner()
    qtbot.addWidget(banner)
    banner.update_status(FakeStatus(state="trial_active", days_left=1))
    assert "1 day left" in banner.label.text()


def test_banner_expired_shows_buy_button(qtbot):
    clicked = []
    banner = TrialBanner(on_buy=lambda: clicked.append(1))
    qtbot.addWidget(banner)
    banner.update_status(FakeStatus(state="trial_expired"))
    assert "expired" in banner.label.text().lower()
    banner.buy_button.click()
    assert clicked == [1]


def _button_shown(banner: TrialBanner) -> bool:
    """isVisible() is False for never-shown offscreen widgets; check hidden flag."""
    return not banner.buy_button.isHidden()


def test_banner_licensed_hides_buy(qtbot):
    banner = TrialBanner()
    qtbot.addWidget(banner)
    banner.update_status(FakeStatus(state="licensed"))
    assert "Licensed" in banner.label.text()
    assert not _button_shown(banner)


def test_banner_tampered(qtbot):
    banner = TrialBanner()
    qtbot.addWidget(banner)
    banner.update_status(FakeStatus(state="tampered", detail="signature invalid"))
    assert "integrity" in banner.label.text().lower()
    assert _button_shown(banner)


def test_banner_none_status(qtbot):
    banner = TrialBanner()
    qtbot.addWidget(banner)
    banner.update_status(None)
    assert "unknown" in banner.label.text().lower()
