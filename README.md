<p align="center">
  <img src="media/logo.png" alt="py-Rizmi Licensing" width="200"/>
</p>

<h1 align="center">py-Rizmi Licensing</h1>

<p align="center">
  Offline RSA-signed license issuance, validation, and viewing —<br>
  with a PyQt6 GUI, CLI scripts, and a fully testable Python API.
</p>

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Quick Start](#quick-start)
5. [GUI Usage Guide](#gui-usage-guide)
6. [CLI Scripts](#cli-scripts)
7. [Python API / Backend Integration](#python-api--backend-integration)
8. [Testing](#testing)
9. [Project Structure](#project-structure)
10. [Contributing](#contributing)
11. [License](#license)

---

## Overview

**py-Rizmi Licensing** enables you to issue, validate, and inspect
offline RSA-signed license files using JWT tokens. It is built for deployment
environments where internet access is unavailable — the license is validated
locally using a public key and a hardware fingerprint (HWID).

The entire core layer is pure Python with zero GUI dependencies, making it
suitable for integration into any Python application or web backend.

---

## Features

- **RSA Keypair Management** — Generate (2048/3072/4096-bit), load, paste,
  and validate RSA keypairs. Verify that private and public keys match.
- **Machine Fingerprinting** — Deterministic SHA-256 hardware ID based on
  MAC address, hostname, and OS.
- **License Issuance** — Sign arbitrary payload fields into a JWT token
  and save as a `.lic` file.
- **License Validation** — Verify signature, expiration, and HWID match
  on any machine.
- **License Viewer** — Decode and inspect any `.lic` file with the
  matching public key — no private key needed.
- **Integration Guide** — In-app rendered README with Python API docs
  and backend integration examples.
- **PyQt6 GUI** — Sidebar-navigated desktop application for cross-platform use.
- **CLI Scripts** — Headless issuance, key generation, and HWID retrieval
  for server-side automation.
- **Backend Module** — Drop-in validation function for app-server integration.
- **Fully Tested** — 34 pytest tests covering all core logic.

---

## Architecture

```
core/     ← Pure Python. No GUI. 100% testable.
gui/      ← PyQt6 widgets. Depends on core/.
scripts/  ← Thin CLI wrappers around core/.
backend/  ← Server-side validation helper. Depends on core/.
tests/    ← pytest suite. Imports only core/.
```

Every payload field is a bound input widget — there is zero hard-coded
payload data anywhere in the codebase.

---

## Quick Start

```bash
# 1. Install dependencies (pip or uv)
pip install -r requirements.txt
```

You have **two ways** to use the toolkit:

### 🖥️  GUI Mode

Launch the full desktop application with sidebar navigation:

```bash
python main.py
```

All features — key generation, license issuance, viewer, and the
integration guide — are accessible through the interface.

### ⌨️  CLI Mode

Use the headless scripts for automation or server-side workflows:

```bash
# Generate an RSA keypair
python scripts/gen_keypair.py \
  --private-out keys/private_key.pem \
  --public-out keys/public_key.pem \
  --key-size 2048

# Get this machine's hardware fingerprint
python scripts/get_machine_id.py

# Issue a signed license file
python scripts/issue_license.py \
  --private-key keys/private_key.pem \
  --output license.lic \
  --client "Acme Corp" \
  --license-id "deploy-001" \
  --hwid "<paste-the-hwid-here>" \
  --features billing reports \
  --max-clients 10 \
  --exp-days 365
```

---

## GUI Usage Guide

The application opens a window with a **sidebar** on the left and a content
area on the right. Click any navigation item to switch views.

### Machine ID

1. Click **Generate Machine ID**.
2. The raw fingerprint and SHA-256 hash are displayed.
3. Click **Copy HWID** and send this hash to your license issuer.

### Key Management

Generate, load, and validate RSA keypairs.

1. **① Generate Keypair** — Select key size (2048, 3072, or 4096) and click
   **Generate**. The private and public PEM are displayed in read-only text
   areas. Use **Save** and **Copy** to export or copy each key.
2. **② Load Keys** — Browse for existing `.pem` files on disk, or **Paste**
   PEM content from the clipboard.
3. **③ Validate Pair** — Click **Validate Keypair** to confirm both PEMs
   belong together. Result shows key size or a mismatch error.

### License Generation

1. **① Signing Key** — Browse for an existing private key `.pem` file.
2. **② License Payload** — Fill in every field:
   - Client / Deployment (required)
   - License ID (required)
   - HWID (required — click **← Tab 1** to pull from Machine ID view)
   - Features (add/remove dynamically)
   - Max Clients, Mode, Server URL, Grace Days
   - Issued At (iat) and Expiration (exp) — auto or manual.
3. Click **Preview Payload (JSON)** to inspect the data before signing.
4. Click **Generate License** and save the `.lic` file.

### License Viewer

1. Select the matching **public key** `.pem` file.
2. Select the **license file** `.lic` to inspect.
3. Click **Decode & View** — all fields are displayed read-only, along
   with expiry status and days remaining.

### Integration Guide

In-app rendered view of this README — Python API docs, CLI usage, and
backend integration instructions.

---

## CLI Scripts

All scripts are in the `scripts/` directory.

### Generate a Keypair

```bash
python scripts/gen_keypair.py \
  --private-out keys/private_key.pem \
  --public-out keys/public_key.pem \
  --key-size 2048
```

### Get Machine HWID

Run this on the target deployment machine:

```bash
python scripts/get_machine_id.py
# Raw fingerprint: 00:1a:2b:3c:4d:5e-server-xyz-Linux
# HWID (SHA-256): a1b2c3d4e5f6...
```

### Issue a License

Run this on your license-authoring machine:

```bash
python scripts/issue_license.py \
  --private-key keys/private_key.pem \
  --output license.lic \
  --client "Acme Corp" \
  --license-id "deploy-001" \
  --hwid "<paste the HWID here>" \
  --features billing reports \
  --max-clients 10 \
  --mode offline \
  --grace-days 14 \
  --exp-days 365
```

---

## Python API / Backend Integration

You can use the core modules directly in any Python application.

### Hardware Identifier

```python
from src.core.hwid import HardwareIdentifier

# Get the current machine's HWID
hwid = HardwareIdentifier.get_machine_id()

# Verify a HWID against this machine
is_match = HardwareIdentifier.verify(some_hwid)
```

### Keypair Management

```python
from src.core.keypair import KeyPairManager

# Generate in-memory
priv_pem, pub_pem = KeyPairManager.generate_keypair()

# Generate with custom key size
priv_pem, pub_pem = KeyPairManager.generate_keypair(key_size=4096)

# Save to disk
KeyPairManager.save_keypair("keys/private.pem", "keys/public.pem")

# Load existing keys
priv = KeyPairManager.load_private_key("keys/private.pem")
pub = KeyPairManager.load_public_key("keys/public.pem")

# Validate individual key format
KeyPairManager.validate_private_key(priv_pem)   # True / False
KeyPairManager.validate_public_key(pub_pem)      # True / False

# Verify that a private and public key belong together
KeyPairManager.verify_keypair(priv_pem, pub_pem)  # True / False

# Get key size in bits
KeyPairManager.get_key_size(priv_pem)             # 2048, 4096, or None
```

### License Payload

```python
from src.core.license_token import LicensePayload

payload = LicensePayload(
    client="MyApp",
    license_id="lic-001",
    hwid="<machine-hwid>",
    features=["billing", "reports"],
    max_clients=5,
    mode="offline",
)
payload.set_auto_iat()
payload.set_auto_exp(days=365)

# Serialise / deserialise
data = payload.to_dict()
restored = LicensePayload.from_dict(data)
```

### Issue a License

```python
from src.core.license_issuer import LicenseIssuer
from src.core.license_token import LicensePayload

payload = LicensePayload(client="Acme", license_id="lic-001", hwid="...")
payload.set_auto_iat()
payload.set_auto_exp(365)

issuer = LicenseIssuer.from_file("keys/private_key.pem")
token = issuer.issue(payload)              # returns JWT string
issuer.issue_to_file(payload, "license.lic")  # writes to file
```

### Validate a License

```python
from src.core.license_validator import LicenseValidator

validator = LicenseValidator.from_file("keys/public_key.pem")

# Full validation (signature + expiry + HWID)
try:
    payload = validator.validate(token)
    print(f"Valid license for {payload.client}")
except ValueError as e:
    print(f"Validation failed: {e}")  # "expired", "tampered", "hwid_mismatch", etc.

# Decode without validation (read-only viewer mode)
data = validator.decode_token(token)
print(data["features"])
```

### Server-Side Drop-In

For a deployment server, use the ready-made `backend` module:

```python
from backend.license_check import validate_license

try:
    payload = validate_license("/path/to/config/dir")
    # config dir must contain public_key.pem and license.lic
    print(payload["client"], payload["features"])
except ValueError as exc:
    print(f"License invalid: {exc}")
```

---

## Testing

```bash
pip install -e ".[dev]"
pytest -v
```

All 34 tests cover the core layer without any GUI dependencies.

---

## Project Structure

```
py-rizmi/
├── main.py                          # GUI entry point
├── requirements.txt
├── pyproject.toml
├── .gitignore
├── README.md
├── media/
│   └── logo.png                     # Application logo
├── config/
│   ├── __init__.py
│   └── settings.py                  # Central configuration
├── src/
│   ├── __init__.py
│   ├── core/                        # Pure logic — no GUI
│   │   ├── __init__.py
│   │   ├── hwid.py                  # Machine fingerprint
│   │   ├── keypair.py               # RSA keypair management
│   │   ├── license_token.py         # Token data model
│   │   ├── license_issuer.py        # Token signing
│   │   └── license_validator.py     # Token validation + decode
│   ├── gui/                         # PyQt6 GUI
│   │   ├── __init__.py
│   │   ├── app.py                   # Main window + sidebar
│   │   ├── theme.py                 # Styling & theming
│   │   ├── views/
│   │   │   ├── __init__.py
│   │   │   ├── hwid_view.py         # Machine ID view
│   │   │   ├── keymanager_view.py   # Key Management view
│   │   │   ├── generate_view.py     # License Generation view
│   │   │   ├── viewer_view.py       # License Viewer view
│   │   │   └── guide_view.py        # Integration Guide view
│   │   └── widgets/
│   │       ├── __init__.py
│   │       ├── step_card.py         # Numbered card widget
│   │       └── dynamic_list.py      # Add/remove list widget
│   └── utils/
│       ├── __init__.py
│       └── logger.py
├── scripts/                         # CLI versions
│   ├── gen_keypair.py
│   ├── get_machine_id.py
│   └── issue_license.py
├── backend/                         # Server-side validation
│   ├── __init__.py
│   └── license_check.py
├── keys/                            # Generated keys (gitignored)
│   └── .gitkeep
└── tests/                           # pytest suite
    ├── __init__.py
    ├── conftest.py
    ├── test_hwid.py
    ├── test_keypair.py
    ├── test_license_token.py
    ├── test_license_issuer.py
    └── test_license_validator.py
```

---

## Contributing

Contributions are welcome and appreciated! Here's how you can help:

### Getting Started

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/my-feature`.
3. Install dev dependencies: `pip install -e ".[dev]"`.
4. Make your changes.
5. Run the tests: `pytest -v` — all must pass.
6. Commit with a clear message: `git commit -m "Add my feature"`.
7. Push and open a Pull Request.

### Guidelines

- Keep the **core layer pure** — no GUI or I/O imports in `src/core/`.
- Add **tests** for any new functionality.
- Follow existing code style (type annotations, no hard-coded strings in
  payload, dataclasses for models).
- Update the **README** if you add or change user-facing features.

### Reporting Issues

- Use the GitHub issue tracker.
- Include the full error output and steps to reproduce.
- Mention your Python version and operating system.

### Ideas for Contributions

- Online validation mode (server-side ping endpoint).
- Certificate Revocation List (CRL) support.
- Tamper-evident audit log with rolling SHA-256 chains.
- Key rotation via `key_id` in JWT headers.
- Packaging as a distributable (`pip install`).

---

## License

This project is provided under the MIT License. See the `LICENSE` file for details.
