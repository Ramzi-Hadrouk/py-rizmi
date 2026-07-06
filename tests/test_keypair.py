from src.core.keypair import KeyPairManager


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
