
from py_rizmi.core.keypair import KeyPairManager


def test_generate_returns_pem_strings():
    priv, pub = KeyPairManager.generate_keypair()
    assert "PRIVATE KEY" in priv
    assert "PUBLIC KEY" in pub


def test_save_and_load(tmp_path):
    priv_path = tmp_path / "private.pem"
    pub_path = tmp_path / "public.pem"
    KeyPairManager.save_keypair(str(priv_path), str(pub_path))

    assert priv_path.exists()
    assert pub_path.exists()

    loaded_priv = KeyPairManager.load_private_key(str(priv_path))
    loaded_pub = KeyPairManager.load_public_key(str(pub_path))
    assert "PRIVATE KEY" in loaded_priv
    assert "PUBLIC KEY" in loaded_pub


# ---------- validation ----------


def test_validate_private_key_valid():
    priv, _ = KeyPairManager.generate_keypair()
    assert KeyPairManager.validate_private_key(priv) is True


def test_validate_private_key_invalid():
    assert KeyPairManager.validate_private_key("not a key") is False
    assert KeyPairManager.validate_private_key("") is False


def test_validate_public_key_valid():
    _, pub = KeyPairManager.generate_keypair()
    assert KeyPairManager.validate_public_key(pub) is True


def test_validate_public_key_invalid():
    assert KeyPairManager.validate_public_key("not a key") is False
    assert KeyPairManager.validate_public_key("") is False


def test_verify_keypair_matching():
    priv, pub = KeyPairManager.generate_keypair()
    assert KeyPairManager.verify_keypair(priv, pub) is True


def test_verify_keypair_mismatched():
    priv1, _ = KeyPairManager.generate_keypair()
    _, pub2 = KeyPairManager.generate_keypair()
    assert KeyPairManager.verify_keypair(priv1, pub2) is False


def test_verify_keypair_invalid_input():
    assert KeyPairManager.verify_keypair("bad", "also bad") is False
    assert KeyPairManager.verify_keypair("", "") is False


def test_verify_keypair_swapped():
    priv, pub = KeyPairManager.generate_keypair()
    # passing public as private and vice versa should fail
    assert KeyPairManager.verify_keypair(pub, priv) is False


def test_validate_cross_key_size():
    priv, pub = KeyPairManager.generate_keypair(key_size=4096)
    assert KeyPairManager.validate_private_key(priv) is True
    assert KeyPairManager.validate_public_key(pub) is True
    assert KeyPairManager.verify_keypair(priv, pub) is True


def test_get_key_size():
    priv, pub = KeyPairManager.generate_keypair(key_size=2048)
    assert KeyPairManager.get_key_size(priv) == 2048
    assert KeyPairManager.get_key_size(pub) == 2048


def test_get_key_size_invalid():
    assert KeyPairManager.get_key_size("garbage") is None
