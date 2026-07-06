# License Management Tool

Offline RSA-signed license issuance, validation, and viewing — with a
three-tab tkinter GUI and a fully testable core layer.

## Quick Start

```bash
pip install -r requirements.txt

# Launch the GUI
python main.py
```

## GUI Tabs

| Tab | Purpose |
|-----|---------|
| **1. Machine ID** | Generate the SHA-256 hardware fingerprint for the current machine. Copy it and send to the license issuer. |
| **2. License Generation** | Fill in every payload field via input widgets (client, license_id, HWID, features, max_clients, mode, server_url, grace_days, iat, exp). Browse for a private key (or generate a new keypair). Sign and save a `.lic` file. |
| **3. License Viewer** | Load any `.lic` file + the matching public key to view decoded fields read-only. Shows expiry status and days remaining. |

## CLI Scripts

```bash
# Generate keypair
python scripts/gen_keypair.py --private-out keys/private_key.pem --public-out keys/public_key.pem

# Get machine ID (run on deployment server)
python scripts/get_machine_id.py

# Issue a license (run on your machine)
python scripts/issue_license.py \
  --private-key keys/private_key.pem \
  --output license.lic \
  --client "Acme Corp" \
  --license-id "deploy-001" \
  --hwid "<paste from get_machine_id.py>" \
  --features billing reports \
  --max-clients 10 \
  --mode offline \
  --grace-days 14 \
  --exp-days 365
```

## Backend (Deployment Server)

Place `public_key.pem` and `license.lic` in `app-server/config/`, then:

```python
from backend.license_check import validate_license

payload = validate_license("app-server/config")
print(payload["client"], payload["features"])
```

## Testing

```bash
pip install -e ".[dev]"
pytest -v
```

## Architecture

```
core/   ← pure Python, no GUI imports, 100% testable
gui/    ← tkinter widgets, depends on core/
scripts/← thin CLI wrappers around core/
backend/← server-side validation, depends on core/
tests/  ← pytest, imports only core/
```

Every payload field is a bound input widget — there is zero hard-coded
payload data anywhere in the codebase.
