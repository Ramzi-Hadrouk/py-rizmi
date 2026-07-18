"""Server-side license validation module.

Drop this into app-server/config/ alongside public_key.pem and license.lic.
"""
import logging
import os
from typing import Any

from py_rizmi.core.license_validator import LicenseValidator

logger = logging.getLogger("license")


def current_hwid() -> str:
    """Convenience wrapper — kept for backward-compat with v5 scripts."""
    from py_rizmi.core.hwid import HardwareIdentifier
    return HardwareIdentifier.get_machine_id()


def get_public_key(config_dir: str) -> str:
    with open(os.path.join(config_dir, "public_key.pem")) as f:
        return f.read()


def validate_license(config_dir: str) -> dict[str, Any]:
    """Validate license.lic in *config_dir*. Returns payload dict on success.

    Raises ValueError with one of: 'missing', 'decode_error', 'tampered',
    'invalid_algorithm', 'unsupported_schema', 'expired', 'hwid_mismatch'.
    See py_rizmi.core.license_validator.ERROR_MESSAGES for human-readable text.
    """
    public_key = get_public_key(config_dir)
    license_path = os.path.join(config_dir, "license.lic")

    try:
        with open(license_path) as f:
            token = f.read().strip()
    except FileNotFoundError:
        logger.warning("License check failed: missing license.lic")
        raise ValueError("missing")

    validator = LicenseValidator(public_key)

    try:
        payload = validator.validate(token, check_hwid=True)
    except ValueError:
        raise

    logger.info(
        "License check passed for %s (exp=%s)",
        payload.client, payload.exp,
    )
    return payload.to_dict()
