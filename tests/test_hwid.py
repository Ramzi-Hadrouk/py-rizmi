import re
from src.core.hwid import HardwareIdentifier


def test_machine_id_is_64_char_hex():
    hwid = HardwareIdentifier.get_machine_id()
    assert isinstance(hwid, str)
    assert len(hwid) == 64
    assert re.match(r"^[0-9a-f]{64}$", hwid)


def test_machine_id_is_deterministic():
    assert HardwareIdentifier.get_machine_id() == HardwareIdentifier.get_machine_id()


def test_raw_fingerprint_nonempty():
    assert len(HardwareIdentifier.get_raw_fingerprint()) > 0


def test_verify_self():
    assert HardwareIdentifier.verify(HardwareIdentifier.get_machine_id())


def test_verify_wrong():
    assert not HardwareIdentifier.verify("deadbeef" * 8)
