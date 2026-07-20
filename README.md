<p align="center">
  <img
    src="https://raw.githubusercontent.com/Ramzi-Hadrouk/py-rizmi/main/media/logo.png"
    alt="py-Rizmi Licensing"
    width="200"
  />
</p>

<h1 align="center">py-Rizmi Licensing</h1>

<p align="center">
  <a href="https://github.com/Ramzi-Hadrouk/py-rizmi/actions/workflows/ci.yml">
    <img src="https://github.com/Ramzi-Hadrouk/py-rizmi/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <a href="https://pypi.org/project/py-rizmi/">
    <img src="https://img.shields.io/pypi/v/py-rizmi" alt="PyPI">
  </a>
  <img src="https://img.shields.io/pypi/pyversions/py-rizmi" alt="Python >=3.12">
  <a href="https://github.com/Ramzi-Hadrouk/py-rizmi/blob/main/LICENSE">
    <img src="https://img.shields.io/pypi/l/py-rizmi" alt="MIT">
  </a>
</p>

<p align="center">
py-Rizmi is an offline-first licensing toolkit that helps developers protect and distribute Python software through cryptographically signed licenses,
hardware-bound activation, and secure local validation, while remaining flexible for future online licensing workflows.
</p>

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Quick Start](#quick-start)
5. [GUI Usage Guide](#gui-usage-guide)
6. [CLI Reference](#cli-reference)
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
  the OS-level machine identifier. Pluggable via `FingerprintProvider` Protocol.
- **License Issuance** — Sign arbitrary payload fields into a JWT token
  and save as a `.lic` file with `schema_version` for future-proofing.
- **License Validation** — Verify signature, expiration (with grace period
  enforcement), and HWID match on any machine.
- **License Viewer** — Decode and inspect any `.lic` file with the
  matching public key — no private key needed.
- **Integration Guide** — In-app rendered README with Python API docs
  and backend integration examples.
- **Public API** — Curated `__all__` surface (`LicenseValidator`,
  `LicenseIssuer`, `KeyPair`, `MachineFingerprint`, `LicensePayload`)
  covered by SemVer.
- **PyQt6 GUI** — Sidebar-navigated desktop application for cross-platform use.
- **CLI** — Headless issuance, key generation, validation, and HWID retrieval
  via `rizmi` commands (Typer + Rich).
- **Backend Module** — Drop-in validation function for app-server integration.
- **Fully Tested** — 60+ pytest tests with Hypothesis property tests, contract
  tests, regression tests, e2e tests, GUI tests, and ruff + mypy enforcement.

---

## Architecture

```
py_rizmi/core/          ← Pure Python. No GUI. 100% testable.
py_rizmi/models/        ← LicensePayload dataclass with schema_version.
py_rizmi/integrations/  ← Server-side validation helper.
py_rizmi/gui/           ← PyQt6 widgets. Depends on core/. Optional [gui] extra.
py_rizmi/cli/           ← Typer CLI (rizmi command). Depends on core/.
py_rizmi/_internal/     ← Private implementation — never import directly.
tests/                  ← pytest suite. Imports only core/.
```

Fingerprint sources implement the `FingerprintProvider` Protocol, making
the fingerprinting layer extensible without modifying core code.

Every payload field is a bound input widget — there is zero hard-coded
payload data anywhere in the codebase.

---

## Quick Start

```bash
# Recommended — with uv (uses the lockfile for reproducible installs)
uv sync --extra dev          # development (core + test tools)
uv sync --extra gui          # with GUI support
uv sync --extra all          # everything

# With pip (manually resolve dependencies)
pip install py-rizmi          # core only
pip install py-rizmi[gui]     # with GUI
pip install -e ".[dev]"       # local development
```

You have **two ways** to use the toolkit:

### 🖥️  GUI Mode

Launch the full desktop application with sidebar navigation:

```bash
# Recommended (installed package)
rizmi gui

# Alternative (run directly from repo)
python main.py
```

> **Requires the `[gui]` extra.** If not installed, `rizmi gui` will print a
> friendly install hint instead of crashing. Install with:
> ```bash
> pip install py-rizmi[gui]
> # or with uv:
> uv sync --extra gui
> ```

All features — key generation, license issuance, viewer, and the
integration guide — are accessible through the interface.

### ⌨️  CLI Mode

The `rizmi` command (Typer + Rich) provides headless access to all features:

```bash
# Generate an RSA keypair
rizmi keys generate \
  --private-out keys/private_key.pem \
  --public-out keys/public_key.pem \
  --key-size 2048 \
  --passphrase

# Get this machine's hardware fingerprint
rizmi machine-id

# Issue a signed license file
rizmi license issue \
  --private-key keys/private_key.pem \
  --output license.lic \
  --client "Acme Corp" \
  --license-id "deploy-001" \
  --hwid "<paste-the-hwid-here>" \
  --features billing --features reports \
  --max-clients 10 \
  --grace-days 14 \
  --exp-days 365

# Validate and inspect a license
rizmi license validate license.lic --public-key keys/public_key.pem
rizmi license inspect license.lic --public-key keys/public_key.pem
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

## CLI Reference

The `rizmi` CLI is the recommended interface for all headless operations.
Every command supports `--help` / `-h`:

```bash
rizmi --help
rizmi keys --help
rizmi license --help
rizmi machine-id --help
rizmi gui --help
```

### Key Management — `rizmi keys`

| Command | Description |
|---|---|
| `rizmi keys generate` | Generate a new RSA keypair (2048 / 3072 / 4096 bits) |
| `rizmi keys inspect <key.pem>` | Show key type, size, and fingerprint |
| `rizmi keys verify --private ... --public ...` | Verify a private/public key pair matches |

### License Operations — `rizmi license`

| Command | Description |
|---|---|
| `rizmi license issue` | Sign and write a `.lic` token file |
| `rizmi license validate <file.lic>` | Validate signature, expiry, and HWID |
| `rizmi license inspect <file.lic>` | Decode and display all payload fields |

### Machine Fingerprint — `rizmi machine-id`

```bash
rizmi machine-id           # rich panel output
rizmi machine-id --raw     # plain hash only (for piping)
rizmi machine-id --copy    # copy to clipboard
```

### GUI — `rizmi gui`

```bash
rizmi gui                  # launch the PyQt6 desktop application
```

Requires the `[gui]` extra (`pip install py-rizmi[gui]`). Without it,
the command exits with code `1` and prints a clear install hint.

### Full Example Workflow

```bash
# 1. Generate keys
rizmi keys generate --private-out keys/private.pem --public-out keys/public.pem

# 2. Get HWID of the target machine
rizmi machine-id --raw

# 3. Issue a license
rizmi license issue \
  --private-key keys/private.pem \
  --output license.lic \
  --client "Acme Corp" \
  --license-id "deploy-001" \
  --hwid "<hwid-from-step-2>" \
  --features billing --features reports \
  --exp-days 365

# 4. Validate on the target machine
rizmi license validate license.lic --public-key keys/public.pem

# 5. Inspect a token (author side, no HWID check)
rizmi license inspect license.lic --public-key keys/public.pem
```

> To protect the private key at rest, add `--passphrase` to `keys generate`.
> When issuing with an encrypted key, pass `--key-passphrase` or set
> the `RIZMI_KEY_PASSPHRASE` environment variable.

---

## Integration Workflow — From Start to Finish

The recommended path is to use **`rizmi gui`** (or `python main.py`) for interactive
tasks and fall back to **CLI commands** (`rizmi ...`) when you need
to automate or work on a headless server.

### Step 1 — Generate an RSA Keypair

**GUI (recommended):** Open the app → **Key Management** view → pick a key
size → click **Generate** → **Save** both `.pem` files.

**CLI (headless/automation):**
```bash
rizmi keys generate \
  --private-out keys/private_key.pem \
  --public-out keys/public_key.pem \
  --key-size 2048
```

> 🔒 `private_key.pem` stays on your authoring machine — never ship it.

### Step 2 — Get the Machine HWID

**Run this on the target machine** where the licensed app will be deployed.

**GUI (recommended):** Open the app (`rizmi gui`) → **Machine ID** view → click
**Generate Machine ID** → **Copy HWID**.

**CLI (headless server):**
```bash
rizmi machine-id
# HWID (SHA-256): fb50b7767d233a9ecc952dd9c11760586b3bd1a40d6bfbec051a312f0b51c77c
```

Send this hash to your license author.

### Step 3 — Issue a License

**GUI (recommended):** Open the app → **License Generation** view →
select the private key, fill in the payload fields (including the HWID
from Step 2), add features, set dates → **Generate License**.

**CLI (headless/automation):**
```bash
rizmi license issue \
  --private-key keys/private_key.pem \
  --output license.lic \
  --client "Acme Corp" \
  --license-id "deploy-001" \
  --hwid "<paste-hwid-here>" \
  --features billing --features reports \
  --max-clients 10 \
  --exp-days 365
```

Deliver `public_key.pem` and `license.lic` to the developer integrating
the app.

### Step 4 — Integrate Validation Into Your App

The developer embeds `public_key.pem` and `license.lic` and validates
at startup — no GUI or script needed here, just the Python API:

```python
from py_rizmi import LicenseValidator

validator = LicenseValidator.from_file("path/to/public_key.pem")

try:
    payload = validator.validate_from_file("path/to/license.lic")
    print(f"Licensed to {payload.client}")
    if payload.in_grace_period:
        print("Warning: license is in grace period")
except ValueError as e:
    print(f"License invalid: {e}")
```

### Step 5 — Server-Side Drop-In (Optional)

For apps with a validation server:

```python
from py_rizmi.integrations.validation import validate_license

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
# Fast unit tests (no GUI dependencies)
uv run pytest -p no:qt tests/unit -v

# Full test suite (requires PyQt6 + system libEGL)
uv run pytest -v

# Linting & type checking
uv run ruff check .
uv run mypy src

# With pip (no lockfile)
pip install -e ".[dev,gui]"
pytest -v
```

All core tests cover the public API without any GUI dependencies.

---

## Building an Executable

This project uses [Nuitka](https://nuitka.net) to compile the Python code
into a standalone native executable for Linux or Windows.

### Prerequisites

```bash
# Nuitka is a dev dependency
uv sync --extra dev

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
├── pyproject.toml                   # Hatchling + hatch-vcs build config
├── build.sh                         # Nuitka build script
├── CHANGELOG.md                     # Keep-a-Changelog
├── CONTRIBUTING.md                  # Development guide
├── docs/
│   ├── api-stability.md             # SemVer policy
│   └── adr/
│       └── 0001-pyqt6-licensing.md  # Architecture Decision Record
├── .github/workflows/
│   ├── ci.yml                       # CI: lint + fast tests + full tests
│   └── release.yml                  # Release: build → TestPyPI → PyPI → GitHub Release
├── media/
│   └── logo.png                     # Application logo
├── src/
│   └── py_rizmi/
│       ├── __init__.py              # Public API (__all__)
│       ├── _version.py              # hatch-vcs generated (gitignored)
│       ├── core/                    # Pure logic — no GUI
│       │   ├── crypto.py            # RSA primitives
│       │   ├── hwid.py              # Machine fingerprint + FingerprintProvider Protocol
│       │   ├── keypair.py           # RSA keypair management
│       │   ├── license_issuer.py    # Token signing
│       │   └── license_validator.py # Token validation + decode
│       ├── models/
│       │   └── license_payload.py   # LicensePayload dataclass with schema_version
│       ├── gui/                     # PyQt6 GUI (optional [gui] extra)
│       │   ├── app.py               # Main window + sidebar
│       │   ├── theme.py             # Styling & theming
│       │   ├── views/
│       │   │   ├── hwid_view.py
│       │   │   ├── keymanager_view.py
│       │   │   ├── generate_view.py
│       │   │   ├── viewer_view.py
│       │   │   └── guide_view.py
│       │   └── widgets/
│       │       ├── step_card.py
│       │       └── dynamic_list.py
│       ├── integrations/
│       │   └── validation.py        # Server-side validation helper
│       ├── cli/                     # rizmi CLI (Typer + Rich)
│       │   ├── app.py               # Root app + help banner + --version
│       │   └── commands/
│       │       ├── keys.py          # keys generate / inspect / verify
│       │       ├── license_cmd.py   # license issue / validate / inspect
│       │       └── machine_id.py    # machine-id (--raw, --copy)
│       └── _internal/               # Private — never import directly
│           └── logging.py
├── keys/                            # Generated keys (gitignored)
│   └── .gitkeep
└── tests/                           # comprehensive pytest suite
    ├── unit/
    │   ├── core/                      # Core cryptography unit tests
    │   └── models/                    # Data model unit tests
    ├── integration/                 # Hypothesis property tests
    ├── contract/                    # Golden fixtures and compatibility checks
    ├── regression/                  # Specific bug repro/regression tests
    ├── e2e/                         # CLI execution smoke tests
    └── gui/                         # PyQt6 widget and workflow tests
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full development guide —
setup, project layout, code style (ruff + mypy), testing, and the
deprecation-shim pattern for public API changes.

### Reporting Issues

- Use the [GitHub issue tracker](https://github.com/Ramzi-Hadrouk/py-rizmi/issues).
- Include the full error output and steps to reproduce.
- Mention your Python version and operating system.

### Ideas for Contributions

Planned post-1.0 features include key rotation, online validation,
certificate revocation lists, and tamper-evident audit logs.

---

## License

This project is provided under the MIT License. See the `LICENSE` file for details.
