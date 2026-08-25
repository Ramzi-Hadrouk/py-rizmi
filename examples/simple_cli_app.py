"""Simple CLI app with py-rizmi licensing — the smallest complete example.

Run me (after `rizmi init MyApp` and issuing a license):
    python examples/simple_cli_app.py
"""
from pathlib import Path

from py_rizmi import LicenseGate, pin_fingerprint

VENDOR_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
...paste your public key here (see rizmi init)...
-----END PUBLIC KEY-----"""
VENDOR_KEY_FINGERPRINT = "...paste fingerprint from rizmi init..."

pin_fingerprint(VENDOR_PUBLIC_KEY, VENDOR_KEY_FINGERPRINT)

gate = LicenseGate(
    app_name="MyCliApp",
    public_key=VENDOR_PUBLIC_KEY,
    config_dir=Path.home() / ".config" / "MyCliApp",
)

status = gate.start()  # first run: starts the trial automatically

if not status:
    print(f"Cannot start: {status.message}")
    print("Activate with: rizmi app activate --app-name MyCliApp --public-key pub.pem --token -")
    raise SystemExit(1)

print(f"Welcome! {status.message}")
# ... your actual application ...
