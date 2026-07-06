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
7. [Integration Workflow](#integration-workflow--from-start-to-finish)
8. [Testing](#testing)
9. [Building an Executable](#building-an-executable)
10. [Project Structure](#project-structure)
11. [Contributing](#contributing)
12. [License](#license)

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
  --grace-days 14 \
  --exp-days 365
```

---

## GUI Usage Guide

The application opens a window with a **sidebar** on the left and a content
area on the right. Click any navigation item to switch views.

### Machine ID

Navigate to **Machine ID** in the sidebar, then:

1. Click **Generate Machine ID**.
2. The raw fingerprint and SHA-256 hash are displayed.
3. Click **Copy HWID** and send this hash to your license issuer.

### Key Management

Navigate to **Key Management** in the sidebar. Generate, load, and validate RSA keypairs.

1. **① Generate Keypair** — Select key size (2048, 3072, or 4096) and click
   **Generate**. The private and public PEM are displayed in read-only text
   areas. Use **Save** and **Copy** to export or copy each key.
2. **② Load Keys** — Browse for existing `.pem` files on disk, or **Paste**
   PEM content from the clipboard.
3. **③ Validate Pair** — Click **Validate Keypair** to confirm both PEMs
   belong together. Result shows key size or a mismatch error.

### License Generation

Navigate to **License Generation** in the sidebar.

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

Navigate to **License Viewer** in the sidebar.

1. Select the matching **public key** `.pem` file.
2. Select the **license file** `.lic` to inspect.
3. Click **Decode & View** — all fields are displayed read-only, along
   with expiry status and days remaining.

### Integration Guide

In-app rendered view of this README — Python API docs, CLI usage, and
backend integration instructions.

---

## CLI Scripts

The three scripts in `scripts/` mirror the core features of the GUI.
All three support `--help` to see available flags:

```bash
python scripts/gen_keypair.py --help
python scripts/get_machine_id.py --help
python scripts/issue_license.py --help
```

Quick-start examples for each are shown in the [CLI Mode](#-cli-mode)
section above.

---

## Integration Workflow — From Start to Finish

The recommended path is to use the **GUI** (`python main.py`) for interactive
tasks and fall back to **CLI scripts** (`python scripts/...`) when you need
to automate or work on a headless server.

### Step 1 — Generate an RSA Keypair

**GUI (recommended):** Open the app → **Key Management** view → pick a key
size → click **Generate** → **Save** both `.pem` files.

**CLI (headless/automation):**
```bash
python scripts/gen_keypair.py \
  --private-out keys/private_key.pem \
  --public-out keys/public_key.pem \
  --key-size 2048
```

> 🔒 `private_key.pem` stays on your authoring machine — never ship it.

### Step 2 — Get the Machine HWID

**Run this on the target machine** where the licensed app will be deployed.

**GUI (recommended):** Open the app → **Machine ID** view → click
**Generate Machine ID** → **Copy HWID**.

**CLI (headless server):**
```bash
python scripts/get_machine_id.py
# HWID (SHA-256): fb50b7767d233a9ecc952dd9c11760586b3bd1a40d6bfbec051a312f0b51c77c
```

Send this hash to your license author.

### Step 3 — Issue a License

**GUI (recommended):** Open the app → **License Generation** view →
select the private key, fill in the payload fields (including the HWID
from Step 2), add features, set dates → **Generate License**.

**CLI (headless/automation):**
```bash
python scripts/issue_license.py \
  --private-key keys/private_key.pem \
  --output license.lic \
  --client "Acme Corp" \
  --license-id "deploy-001" \
  --hwid "<paste-hwid-here>" \
  --features billing reports \
  --max-clients 10 \
  --exp-days 365
```

Deliver `public_key.pem` and `license.lic` to the developer integrating
the app.

### Step 4 — Integrate Validation Into Your App

The developer embeds `public_key.pem` and `license.lic` and validates
at startup — no GUI or script needed here, just the Python API:

```python
from src.core.license_validator import LicenseValidator

validator = LicenseValidator.from_file("path/to/public_key.pem")

try:
    payload = validator.validate("path/to/license.lic")
    print(f"Licensed to {payload['client']}")
except ValueError as e:
    print(f"License invalid: {e}")
```

### Step 5 — Server-Side Drop-In (Optional)

For apps with a validation server:

```python
from backend.license_check import validate_license

try:
    payload = validate_license("/path/to/config/dir")
    # config dir must contain public_key.pem and license.lic
    print(payload["client"], payload["features"])
except ValueError as e:
    print(f"License invalid: {e}")
```

---

## Testing

```bash
pip install -e ".[dev]"
pytest -v

# or with uv
uv run pytest -v
```

All 34 tests cover the core layer without any GUI dependencies.

---

## Building an Executable

This project uses [Nuitka](https://nuitka.net) to compile the Python code
into a standalone native executable for Linux or Windows.

### Prerequisites

```bash
pip install nuitka

# Linux: gcc / g++ must be installed
sudo apt install gcc g++ python3-dev  # Debian / Ubuntu

# Windows: Download and install MSVC from Visual Studio Build Tools
```

### Build

```bash
# Standalone folder (recommended — faster build, easier debugging)
bash build.sh standalone

# Single executable (longer build, larger file)
bash build.sh onefile
```

Output goes to `dist/py-rizmi/`.

> **Cross-platform note:** Build on each target OS separately.
> Linux builds produce Linux binaries, Windows builds produce `.exe`.
> Use GitHub Actions with matrix runners (ubuntu, windows) to automate this.

### What Gets Bundled

| Resource | How | Why |
|----------|-----|-----|
| `media/logo.png` | `--include-data-dir` | Window icon & in-app logo |
| `README.md` | `--include-data-file` | Integration Guide view |
| PyQt6, qdarktheme, markdown, PyJWT, cryptography | Auto-detected by Nuitka | Runtime dependencies |

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
