import time

import pytest
from hypothesis import given
from hypothesis import strategies as st

from py_rizmi.models.license_payload import LicensePayload


def test_to_dict_has_all_fields():
    p = LicensePayload(
        client="C", license_id="L", hwid="H",
        features=["a"], max_clients=3, mode="online",
        server_url="https://x", grace_days=7, iat=100, exp=200,
    )
    d = p.to_dict()
    assert d["client"] == "C"
    assert d["features"] == ["a"]
    assert d["max_clients"] == 3
    assert d["iat"] == 100
    assert d["exp"] == 200


def test_from_dict_roundtrip():
    original = LicensePayload(client="C", license_id="L", hwid="H", features=["x"])
    restored = LicensePayload.from_dict(original.to_dict())
    assert restored == original


def test_set_auto_iat():
    p = LicensePayload()
    before = int(time.time())
    p.set_auto_iat()
    assert before <= p.iat <= int(time.time())


def test_set_auto_exp():
    p = LicensePayload()
    p.set_auto_exp(30)
    expected = int(time.time()) + 30 * 86_400
    assert abs(p.exp - expected) <= 5


def test_defaults():
    p = LicensePayload()
    assert p.max_clients == 10
    assert p.mode == "offline"
    assert p.grace_days == 14
    assert p.features == []


def test_is_expired():
    p = LicensePayload(exp=int(time.time()) - 1)
    assert p.is_expired()
    p.exp = int(time.time()) + 10_000
    assert not p.is_expired()


# ─── Phase 2: strict from_dict validation ------------------------------------


class TestFromDictStrictValidation:
    def test_numeric_string_is_coerced(self):
        p = LicensePayload.from_dict({"max_clients": "25", "grace_days": "7"})
        assert p.max_clients == 25
        assert p.grace_days == 7

    def test_float_integer_is_coerced(self):
        p = LicensePayload.from_dict({"exp": 1234.0})
        assert p.exp == 1234

    def test_fractional_float_rejected(self):
        with pytest.raises(ValueError, match="exp"):
            LicensePayload.from_dict({"exp": 12.5})

    def test_bool_rejected(self):
        with pytest.raises(ValueError, match="max_clients"):
            LicensePayload.from_dict({"max_clients": True})

    def test_non_numeric_string_rejected(self):
        with pytest.raises(ValueError, match="max_clients"):
            LicensePayload.from_dict({"max_clients": "ten"})

    def test_none_rejected(self):
        with pytest.raises(ValueError, match="grace_days"):
            LicensePayload.from_dict({"grace_days": None})

    @pytest.mark.parametrize("field", ["client", "license_id", "hwid", "mode", "server_url"])
    def test_non_string_str_fields_rejected(self, field):
        with pytest.raises(ValueError, match=field):
            LicensePayload.from_dict({field: 123})

    def test_non_list_features_rejected(self):
        with pytest.raises(ValueError, match="features"):
            LicensePayload.from_dict({"features": "pro"})

    def test_non_string_feature_item_rejected(self):
        with pytest.raises(ValueError, match="features"):
            LicensePayload.from_dict({"features": ["pro", 42]})

    def test_negative_grace_days_rejected(self):
        with pytest.raises(ValueError, match="grace_days"):
            LicensePayload.from_dict({"grace_days": -1})

    def test_negative_timestamps_rejected(self):
        with pytest.raises(ValueError, match="iat"):
            LicensePayload.from_dict({"iat": -5})
        with pytest.raises(ValueError, match="exp"):
            LicensePayload.from_dict({"exp": -5})

    def test_unknown_keys_ignored(self):
        p = LicensePayload.from_dict({"future_field": {"nested": True}})
        assert p.client == ""

    def test_empty_dict_yields_defaults(self):
        p = LicensePayload.from_dict({})
        assert p.schema_version == 1
        assert p.max_clients == 10
        assert p.grace_days == 14


@given(st.data())
def test_from_dict_never_crashes_with_unexpected_error(data):
    """Property: from_dict either returns a valid payload or raises ValueError --
    never TypeError/AttributeError/etc, whatever dict it is handed."""
    raw: dict[str, object] = data.draw(
        st.dictionaries(
            st.sampled_from([
                "schema_version", "client", "license_id", "hwid",
                "features", "max_clients", "mode", "server_url",
                "grace_days", "iat", "exp",
            ]),
            st.one_of(
                st.integers(), st.text(), st.booleans(), st.floats(allow_nan=True),
                st.none(), st.lists(st.integers()), st.binary(),
            ),
        )
    )
    try:
        payload = LicensePayload.from_dict(raw)  # type: ignore[arg-type]
    except ValueError:
        return
    # If it accepted the input, round-tripping must preserve every field.
    restored = LicensePayload.from_dict(payload.to_dict())
    assert restored == payload


# ─── Phase 2: grace-period helpers -------------------------------------------


class TestGraceHelpers:
    def test_is_in_grace_false_for_active_license(self):
        p = LicensePayload(exp=int(time.time()) + 86_400)
        assert not p.is_in_grace()

    def test_is_in_grace_true_within_window(self):
        p = LicensePayload(exp=int(time.time()) - 3600, grace_days=14)
        assert p.is_expired()
        assert p.is_in_grace()

    def test_is_in_grace_false_past_window(self):
        p = LicensePayload(exp=int(time.time()) - 20 * 86_400, grace_days=14)
        assert p.is_expired()
        assert not p.is_in_grace()

    def test_is_in_grace_false_for_never_expiring(self):
        p = LicensePayload(exp=0)
        assert not p.is_expired()
        assert not p.is_in_grace()
