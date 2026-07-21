"""Server-side license validation module.

Drop this into app-server/config/ alongside public_key.pem and license.lic.
"""
import importlib.util
import hashlib
import logging
import os
import sys
from pathlib import Path
from typing import Any, List, Tuple

from py_rizmi.core.clock_guard import ClockGuard
from py_rizmi.core.hwid import HardwareIdentifier
from py_rizmi.core.license_validator import LicenseValidator

logger = logging.getLogger("license")

_HAVE_PLATFORMDIRS = importlib.util.find_spec("platformdirs") is not None

# Fixed, non-secret salt used only to derive a stable-but-meaningless
# on-disk filename -- see _obfuscated_name(). Distinct from
# core.clock_guard's own _APP_SALT (that one keys the HMAC and matters
# for tamper detection; this one only affects what the filename *looks
# like*, not whether tampering is caught).
_FILENAME_SALT = b"py-rizmi.integrity-marker.v1"


def current_hwid() -> str:
    """Convenience wrapper - kept for backward-compat with v5 scripts."""
    return HardwareIdentifier.get_machine_id()


def get_public_key(config_dir: str) -> str:
    with open(os.path.join(config_dir, "public_key.pem")) as f:
        return f.read()


def _obfuscated_name(role: str, hidden: bool) -> str:
    """A fixed-but-meaningless filename for *role* -- the same role
    always yields the same name (so we can find our own file again on
    the next run), but nothing about the name suggests clock or license
    data. Each role gets a DIFFERENT name, so finding one copy on disk
    doesn't tell you what the others are called.
    """
    digest = hashlib.sha256(_FILENAME_SALT + b":" + role.encode()).hexdigest()[:16]
    prefix = "." if hidden else ""  # Unix dotfile convention only; see below
    return f"{prefix}{digest}.dat"


def _stdlib_fallback_dirs(app_name: str) -> Tuple[str, str]:
    """Pure-stdlib equivalent of the (local, roaming)-style directory
    pair below, used only if platformdirs somehow isn't installed
    despite being a declared dependency. Intentionally minimal - the
    project's actual recommendation is platformdirs (see the
    implementation plan for why hand-rolling this is worse); this exists
    purely so the feature degrades gracefully instead of hard failing.
    """
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        roaming = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return os.path.join(local, app_name), os.path.join(roaming, app_name)
    if sys.platform == "darwin":
        base = Path.home() / "Library"
        return str(base / "Application Support" / app_name), str(base / "Preferences" / app_name)
    base = Path.home()
    config = os.environ.get("XDG_CONFIG_HOME", str(base / ".config"))
    data = os.environ.get("XDG_DATA_HOME", str(base / ".local" / "share"))
    return os.path.join(config, app_name), os.path.join(data, app_name)


def _platform_dirs(app_name: str) -> Tuple[str, str]:
    """Two distinct, PERSISTENT (never cache/temp) per-user directories:

    - Windows: %LOCALAPPDATA%\\<app>  and  %APPDATA%\\<app> (roaming)
    - macOS:   ~/Library/Application Support/<app>  and  ~/Library/Preferences/<app>
    - Linux:   ~/.config/<app> (XDG_CONFIG_HOME)  and  ~/.local/share/<app> (XDG_DATA_HOME)

    Deliberately never returns a *_cache_dir - those are explicitly
    documented as safe for the OS or cleanup tools to clear, which is
    exactly the opposite of what a rollback high-water mark needs.

    Implementation note: this calls platformdirs' per-OS classes
    (`platformdirs.windows.Windows`, `.macos.MacOS`, `.unix.Unix`)
    directly, selected by our own `sys.platform` check, rather than the
    `platformdirs.user_data_dir()`-style top-level convenience functions.
    Those top-level functions resolve to a specific OS's implementation
    once, the first time the `platformdirs` package is imported in the
    process, and do NOT re-check `sys.platform` on every call - so they
    can't be redirected with `mock.patch("sys.platform", ...)` in a test,
    which is how this was caught. Calling the classes ourselves keeps our
    own OS branch (and therefore this function) genuinely testable for
    all three platforms from a single dev machine.
    """
    if not _HAVE_PLATFORMDIRS:
        return _stdlib_fallback_dirs(app_name)

    if sys.platform == "win32":
        from platformdirs.windows import Windows

        local = Windows(appname=app_name, appauthor=False, roaming=False)
        roaming = Windows(appname=app_name, appauthor=False, roaming=True)
        return local.user_data_dir, roaming.user_data_dir
    if sys.platform == "darwin":
        from platformdirs.macos import MacOS

        # platformdirs' user_data_dir and user_config_dir both resolve to
        # the same "Application Support" path on macOS, so the second
        # location is built by hand from the equally-standard, equally
        # persistent (and platformdirs-unexposed) Preferences directory.
        support = MacOS(appname=app_name, appauthor=False).user_data_dir
        prefs = str(Path.home() / "Library" / "Preferences" / app_name)
        return support, prefs

    from platformdirs.unix import Unix

    unix = Unix(appname=app_name, appauthor=False)
    return unix.user_config_dir, unix.user_data_dir


def _default_state_paths(config_dir: str, app_name: str = "py-rizmi") -> List[str]:
    """Three redundant clock-guard state locations: the caller's own
    *config_dir* (e.g. next to license.lic) plus two OS-conventional
    persistent per-user data directories. Deleting any ONE of the three
    does not disable protection - see core.clock_guard.ClockGuard.

    Pass *app_name* as your own product's name (not "py-rizmi") so the
    two extra directories blend in among your app's other, legitimate
    AppData/`.config`/Application-Support files instead of standing out
    as an unfamiliar third-party folder.
    """
    hidden = sys.platform != "win32"  # dotfiles are a Unix convention;
    # a leading "." looks unusual (and therefore MORE noticeable, the
    # opposite of the goal) inside a normal Windows AppData tree.
    paths = [os.path.join(config_dir, _obfuscated_name("primary", hidden))]
    dir_a, dir_b = _platform_dirs(app_name)
    paths.append(os.path.join(dir_a, _obfuscated_name("a", hidden)))
    paths.append(os.path.join(dir_b, _obfuscated_name("b", hidden)))
    return paths


def _make_clock_guard(config_dir: str, app_name: str = "py-rizmi") -> ClockGuard:
    return ClockGuard(
        _default_state_paths(config_dir, app_name),
        machine_id=HardwareIdentifier.get_machine_id(),
    )


def validate_license(
    config_dir: str, enable_clock_guard: bool = True, app_name: str = "py-rizmi"
) -> dict[str, Any]:
    """Validate license.lic in *config_dir*. Returns payload dict on success.

    *enable_clock_guard* additionally rejects a validation attempt made
    while the system clock looks like it's been rolled back - see
    `py_rizmi.core.clock_guard`. It's on by default since the whole point
    of this function is enforcing a license on a machine that (per the
    project's design) usually has no internet connection to fall back on
    for trusted time. Pass False only for diagnostics/testing.

    *app_name* names the directory used for the two OS-standard redundant
    clock-guard copies (see `_default_state_paths`) - pass your own
    product name here so those directories blend in with your app's
    other data instead of appearing as an unrelated "py-rizmi" folder.

    Raises ValueError whose message is one of the keys in
    `py_rizmi.core.license_validator.ERROR_MESSAGES` - currently:
    'missing', 'expired', 'tampered', 'invalid_algorithm', 'decode_error',
    'unsupported_schema', 'hwid_mismatch', 'revoked', 'clock_tampering'.
    Look up a user-facing message with `ERROR_MESSAGES.get(str(exc), str(exc))`.
    """
    public_key = get_public_key(config_dir)
    license_path = os.path.join(config_dir, "license.lic")

    try:
        with open(license_path) as f:
            token = f.read().strip()
    except FileNotFoundError:
        logger.warning("License check failed: missing license.lic")
        raise ValueError("missing")

    clock_guard = _make_clock_guard(config_dir, app_name) if enable_clock_guard else None
    validator = LicenseValidator(public_key, clock_guard=clock_guard)

    payload = validator.validate(token, check_hwid=True)

    logger.info(
        "License check passed for %s (exp=%s)",
        payload.client, payload.exp,
    )
    return payload.to_dict()
