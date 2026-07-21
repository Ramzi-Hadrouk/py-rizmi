import os
from unittest import mock

import pytest

import py_rizmi.integrations.validation as validation_mod
from py_rizmi.core.hwid import HardwareIdentifier
from py_rizmi.core.keypair import KeyPairManager
from py_rizmi.core.license_issuer import LicenseIssuer
from py_rizmi.models.license_payload import LicensePayload


@pytest.fixture
def config_dir(tmp_path):
    """A config_dir with public_key.pem + license.lic, matching what
    validate_license() expects, plus BOTH OS-standard redundant
    locations redirected into tmp_path so tests never touch the real
    filesystem (~/.config, %LOCALAPPDATA%, ~/Library/..., etc.)."""
    priv, pub = KeyPairManager.generate_keypair()
    (tmp_path / "public_key.pem").write_text(pub)

    hwid = HardwareIdentifier.get_machine_id()
    payload = LicensePayload(client="Acme", license_id="L1", hwid=hwid)
    payload.iat = 3_000_000
    payload.exp = payload.iat + 365 * 86_400
    token = LicenseIssuer(priv).issue(payload)
    (tmp_path / "license.lic").write_text(token)

    dir_a = str(tmp_path / "elsewhere" / "os-location-a")
    dir_b = str(tmp_path / "elsewhere" / "os-location-b")
    with mock.patch.object(validation_mod, "_platform_dirs", return_value=(dir_a, dir_b)):
        yield str(tmp_path), payload, dir_a, dir_b


def test_validate_license_missing_license_file(tmp_path):
    (tmp_path / "public_key.pem").write_text("irrelevant")
    with pytest.raises(ValueError, match="missing"):
        validation_mod.validate_license(str(tmp_path))


def test_validate_license_normal_use(config_dir):
    dir_path, payload, *_ = config_dir
    with mock.patch("time.time", return_value=float(payload.iat)):
        result = validation_mod.validate_license(dir_path)
    assert result["client"] == "Acme"


def test_validate_license_forward_time_is_fine(config_dir):
    dir_path, payload, *_ = config_dir
    with mock.patch("time.time", return_value=float(payload.iat)):
        validation_mod.validate_license(dir_path)
    with mock.patch("time.time", return_value=float(payload.iat + 30 * 86_400)):
        result = validation_mod.validate_license(dir_path)
    assert result["client"] == "Acme"


def test_validate_license_blocks_rollback_by_default(config_dir):
    dir_path, payload, *_ = config_dir
    with mock.patch("time.time", return_value=float(payload.iat)):
        validation_mod.validate_license(dir_path)
    with mock.patch("time.time", return_value=float(payload.iat + 50 * 86_400)):
        validation_mod.validate_license(dir_path)  # advances the high-water mark further

    rollback = payload.iat + 10 * 86_400  # after iat, before the mark established above
    with mock.patch("time.time", return_value=float(rollback)):
        with pytest.raises(ValueError, match="clock_tampering"):
            validation_mod.validate_license(dir_path)


def test_validate_license_enable_clock_guard_false_skips_the_check(config_dir):
    dir_path, payload, *_ = config_dir
    with mock.patch("time.time", return_value=float(payload.iat)):
        validation_mod.validate_license(dir_path)
    with mock.patch("time.time", return_value=float(payload.iat + 50 * 86_400)):
        validation_mod.validate_license(dir_path)

    rollback = payload.iat + 10 * 86_400
    with mock.patch("time.time", return_value=float(rollback)):
        result = validation_mod.validate_license(dir_path, enable_clock_guard=False)
    assert result["client"] == "Acme"


def test_validate_license_writes_state_to_all_three_locations(config_dir):
    dir_path, payload, dir_a, dir_b = config_dir
    with mock.patch("time.time", return_value=float(payload.iat)):
        validation_mod.validate_license(dir_path)

    files_in_config_dir = [
        f
        for f in os.listdir(dir_path)
        if f not in ("public_key.pem", "license.lic")
        and os.path.isfile(os.path.join(dir_path, f))
    ]
    assert len(files_in_config_dir) == 1, "exactly one obfuscated state file alongside license.lic"
    assert len(os.listdir(dir_a)) == 1
    assert len(os.listdir(dir_b)) == 1


def test_two_of_three_locations_surviving_still_blocks_rollback(config_dir):
    """Simulates a user finding and deleting the config_dir copy (the
    most 'discoverable' one, sitting right next to license.lic) - the
    two OS-standard copies must still catch a rollback."""
    dir_path, payload, dir_a, dir_b = config_dir
    with mock.patch("time.time", return_value=float(payload.iat)):
        validation_mod.validate_license(dir_path)
    with mock.patch("time.time", return_value=float(payload.iat + 50 * 86_400)):
        validation_mod.validate_license(dir_path)

    config_dir_files = [
        f
        for f in os.listdir(dir_path)
        if f not in ("public_key.pem", "license.lic")
        and os.path.isfile(os.path.join(dir_path, f))
    ]
    for f in config_dir_files:
        os.remove(os.path.join(dir_path, f))

    rollback = payload.iat + 10 * 86_400
    with mock.patch("time.time", return_value=float(rollback)):
        with pytest.raises(ValueError, match="clock_tampering"):
            validation_mod.validate_license(dir_path)


def test_state_filenames_do_not_contain_revealing_words(config_dir):
    dir_path, payload, dir_a, dir_b = config_dir
    with mock.patch("time.time", return_value=float(payload.iat)):
        validation_mod.validate_license(dir_path)

    all_files = os.listdir(dir_path) + os.listdir(dir_a) + os.listdir(dir_b)
    state_files = [f for f in all_files if f not in ("public_key.pem", "license.lic")]
    assert state_files, "expected at least one state file"
    for name in state_files:
        lowered = name.lower()
        for revealing_word in ("clock", "license", "state", "tamper", "rollback"):
            assert revealing_word not in lowered


def test_the_three_obfuscated_filenames_are_mutually_different(config_dir):
    """Different roles get different names, so finding one copy doesn't
    tell an attacker what the other two are called."""
    dir_path, payload, dir_a, dir_b = config_dir
    with mock.patch("time.time", return_value=float(payload.iat)):
        validation_mod.validate_license(dir_path)

    name_in_config = next(
        f for f in os.listdir(dir_path) if f not in ("public_key.pem", "license.lic")
    )
    name_in_a = os.listdir(dir_a)[0]
    name_in_b = os.listdir(dir_b)[0]
    assert len({name_in_config, name_in_a, name_in_b}) == 3


def test_app_name_changes_the_os_standard_directory_name():
    """A consuming app should be able to pass its OWN product name so the
    two OS-standard directories blend in with its other application data
    instead of appearing as an unrelated 'py-rizmi' folder."""
    with mock.patch.object(validation_mod, "_HAVE_PLATFORMDIRS", False):
        dir_a, dir_b = validation_mod._stdlib_fallback_dirs("ClinicManager")
    assert "ClinicManager" in dir_a
    assert "ClinicManager" in dir_b
    assert "py-rizmi" not in dir_a
    assert "py-rizmi" not in dir_b


# --- Cross-platform path selection ------------------------------------------


def test_linux_paths_avoid_cache_directory():
    with mock.patch("sys.platform", "linux"), mock.patch.dict(
        os.environ, {"HOME": "/home/alice"}, clear=False
    ):
        for k in list(os.environ):
            if k.startswith("XDG_"):
                os.environ.pop(k)
        dir_a, dir_b = validation_mod._platform_dirs("py-rizmi")
    assert ".cache" not in dir_a and ".cache" not in dir_b
    assert dir_a == "/home/alice/.config/py-rizmi"
    assert dir_b == "/home/alice/.local/share/py-rizmi"


def test_windows_paths_avoid_cache_directory():
    win_env = {
        "WIN_PD_OVERRIDE_LOCAL_APPDATA": r"C:\Users\alice\AppData\Local",
        "WIN_PD_OVERRIDE_APPDATA": r"C:\Users\alice\AppData\Roaming",
    }
    with mock.patch("sys.platform", "win32"), mock.patch.dict(os.environ, win_env, clear=False):
        dir_a, dir_b = validation_mod._platform_dirs("py-rizmi")
    assert "Cache" not in dir_a and "Cache" not in dir_b
    assert dir_a != dir_b
    assert "Local" in dir_a and "Roaming" in dir_b


def test_macos_paths_avoid_cache_directory():
    with mock.patch("sys.platform", "darwin"), mock.patch.dict(
        os.environ, {"HOME": "/Users/alice"}, clear=False
    ):
        dir_a, dir_b = validation_mod._platform_dirs("py-rizmi")
    assert "Caches" not in dir_a and "Caches" not in dir_b
    assert dir_a != dir_b
    assert "Application Support" in dir_a
    assert "Preferences" in dir_b
