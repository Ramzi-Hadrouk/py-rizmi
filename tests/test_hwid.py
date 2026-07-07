import re
from unittest.mock import patch

import machineid
import pytest

from src.core.hwid import HardwareIdentifier, MachineIdError

MOCK_GUID = "17A28A73-BEA9-4D4B-AF5B-03A5AAE9B92C"
EXPECTED_HASH = "a31feb8315091cbf62f888a01c43e42d990f49719fb5bc9c07ac9afda73520eb"


@patch("machineid.id", return_value=MOCK_GUID)
def test_machine_id_is_64_char_hex(_):
    hwid = HardwareIdentifier.get_machine_id()
    assert isinstance(hwid, str)
    assert len(hwid) == 64
    assert re.match(r"^[0-9a-f]{64}$", hwid)


@patch("machineid.id", return_value=MOCK_GUID)
def test_machine_id_is_deterministic(_):
    assert HardwareIdentifier.get_machine_id() == HardwareIdentifier.get_machine_id()


@patch("machineid.id", return_value=MOCK_GUID)
def test_machine_id_known_hash(_):
    assert HardwareIdentifier.get_machine_id() == EXPECTED_HASH


@patch("machineid.id", return_value=MOCK_GUID)
def test_verify_self(_):
    hwid = HardwareIdentifier.get_machine_id()
    assert HardwareIdentifier.verify(hwid) is True


@patch("machineid.id", return_value=MOCK_GUID)
def test_verify_wrong(_):
    assert HardwareIdentifier.verify("deadbeef" * 8) is False


@patch("machineid.id", side_effect=machineid.MachineIdNotFound("no id"))
def test_machineid_error_raises(_):
    with pytest.raises(MachineIdError, match="Unable to obtain machine identifier"):
        HardwareIdentifier.get_machine_id()


@patch("machineid.id", side_effect=PermissionError("access denied"))
def test_other_exception_propagates(_):
    with pytest.raises(PermissionError, match="access denied"):
        HardwareIdentifier.get_machine_id()
