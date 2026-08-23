"""Unit tests for LicenseSwapPayload strict from_dict validation."""
import pytest

from py_rizmi.models.swap_payload import LicenseSwapPayload


def test_roundtrip_preserves_fields():
    p = LicenseSwapPayload(
        request_id="r-1", current_license="a", new_license="b",
        issued_at=100, expires_at=200,
    )
    restored = LicenseSwapPayload.from_dict(p.to_dict())
    assert restored == p


class TestFromDictStrictValidation:
    def test_numeric_string_coerced(self):
        p = LicenseSwapPayload.from_dict({"issued_at": "100", "expires_at": "200"})
        assert p.issued_at == 100
        assert p.expires_at == 200

    def test_fractional_float_rejected(self):
        with pytest.raises(ValueError, match="expires_at"):
            LicenseSwapPayload.from_dict({"expires_at": 1.5})

    @pytest.mark.parametrize(
        "field", ["request_id", "current_license", "new_license", "operation"]
    )
    def test_non_string_str_fields_rejected(self, field):
        with pytest.raises(ValueError, match=field):
            LicenseSwapPayload.from_dict({field: ["list"]})

    def test_negative_timestamps_rejected(self):
        with pytest.raises(ValueError, match="issued_at"):
            LicenseSwapPayload.from_dict({"issued_at": -1})
        with pytest.raises(ValueError, match="expires_at"):
            LicenseSwapPayload.from_dict({"expires_at": -1})

    def test_unknown_keys_ignored(self):
        p = LicenseSwapPayload.from_dict({"extra": 1})
        assert p.request_id == ""
