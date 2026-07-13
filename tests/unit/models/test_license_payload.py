import time
from src.core.license_token import LicensePayload


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
