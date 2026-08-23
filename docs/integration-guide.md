# py-rizmi — Developer Integration Guide

> The canonical, no-gaps reference for embedding **py-rizmi** (offline-first,
> RSA-signed licensing) into your Python application. For a shorter tour, see
> the [README](../README.md); for the public-API stability policy, see
> [`docs/api-stability.md`](api-stability.md).

This guide covers **every** integration path:

- **Issuer** (you, the vendor): generate keys, issue licenses, publish
  revocation lists, authorize license swaps.
- **Integrator** (your shipped app): validate licenses at startup, enforce
  trial periods, run a runtime watchdog, and handle every error code.

---

## Table of Contents

1. [Concepts & threat model](#1-concepts--threat-model)
2. [Installation](#2-installation)
3. [The two roles](#3-the-two-roles)
4. [Key management](#4-key-management)
5. [Machine fingerprint (HWID)](#5-machine-fingerprint-hwid)
6. [Issuing licenses](#6-issuing-licenses)
7. [Validating in your app](#7-validating-in-your-app)
8. [Grace period](#8-grace-period)
9. [Error handling](#9-error-handling)
10. [Clock-tamper protection](#10-clock-tamper-protection)
11. [License revocation](#11-license-revocation)
12. [Runtime enforcement (long-running apps)](#12-runtime-enforcement-long-running-apps)
13. [Trial periods (license-free evaluation)](#13-trial-periods-license-free-evaluation)
14. [License swap authorization](#14-license-swap-authorization)
15. [Centralized configuration (RizmiConfig)](#15-centralized-configuration-rizmiconfig)
16. [CLI reference](#16-cli-reference)
17. [GUI overview](#17-gui-overview)
18. [Security & operational caveats](#18-security--operational-caveats)
19. [End-to-end minimal example](#19-end-to-end-minimal-example)
20. [Troubleshooting / FAQ](#20-troubleshooting--faq)

---

## 1. Concepts & threat model

py-rizmi issues **JWT tokens** (`RS256`) that are signed with your **private
RSA key** and validated offline with your **public key**. Each license is bound
to a machine via a **hardware ID (HWID)** — a SHA-256 hash of the OS machine
identifier (`py-machineid`).

Key ideas:

- **Offline-first.** Validation makes **no network calls**. Trusted time is
  enforced locally via a `ClockGuard` high-water mark, not NTP.
- **Public key only ships.** Your app embeds `public_key.pem`. The private key
  never leaves your build/issuing environment.
- **HWID binding.** A license issued for machine A fails on machine B with
  `hwid_mismatch`.
- **Honest threat model.** Like every offline licensing scheme, this *raises
  the bar* against casual-to-moderate tampering (file editing, clock rollback,
  copying another machine's license). It is **not** a defense against a
  determined reverse engineer with a debugger and full disk access. Do not
  treat it as copy-protection for pirate-resistant distribution.

---

## 2. Installation

```bash
# Core only (validation + issuance in-process)
pip install py-rizmi

# With the PyQt6 desktop GUI
pip install py-rizmi[gui]

# Local development (tests, ruff, mypy, nuitka)
pip install -e ".[dev]"

# Everything
pip install -e ".[all]"
```

| Fact | Value |
|---|---|
| PyPI distribution name | `py-rizmi` |
| Import package | `py_rizmi` |
| Python requirement | `>=3.12` |
| Build backend | hatchling + hatch-vcs |
| Version source | git tag (`vX.Y.Z`) via VCS — no manual version edits |
| Console entry point | `rizmi` (→ `py_rizmi.cli.app:main`) |
| Runtime deps | PyJWT, cryptography, typer, rich, py-machineid, platformdirs |

> The GUI (`[gui]` extra) is **optional**. `rizmi gui` and all `py_rizmi.gui`
> imports are deferred so a bare `pip install py-rizmi` never pulls in PyQt6.

---

## 3. The two roles

```
 ┌──────────────────────┐        public_key.pem + license.lic        ┌──────────────────────┐
 │  ISSUER (you)        │  ───────────────────────────────────────▶  │  INTEGRATOR (app)   │
 │  holds private key   │                                            │  embeds public key  │
 │  issues licenses     │  ◀──────── revocation lists / swap auth ──  │  validates at runtime│
 └──────────────────────┘                                            └──────────────────────┘
```

- **Issuer** uses `LicenseIssuer`, the `rizmi license issue` CLI, and key
  management. Never distributes `private_key.pem`.
- **Integrator** uses `LicenseValidator` / `validate_license`, optionally
  `LicenseWatchdog`, `TrialManager`, and a `revocation_list`. Embeds only
  `public_key.pem` and a `license.lic`.

---

## 4. Key management

### CLI

```bash
# Generate a keypair (2048 / 3072 / 4096)
rizmi keys generate \
  --private-out keys/private_key.pem \
  --public-out keys/public_key.pem \
  --key-size 2048 \
  --passphrase                       # encrypt private key with a passphrase

# Inspect any PEM
rizmi keys inspect keys/private_key.pem

# Verify a private/public pair matches
rizmi keys verify --private keys/private_key.pem --public keys/public_key.pem
```

### Python

```python
from py_rizmi.core.crypto import generate_rsa_keypair, save_pem, load_private_key

private_pem, public_pem = generate_rsa_keypair(key_size=2048, passphrase=None)
save_pem(private_pem, "keys/private_key.pem")   # written with 0o600 perms
save_pem(public_pem, "keys/public_key.pem")

# Load later (passphrase from env RIZMI_KEY_PASSPHRASE if omitted interactively)
key = load_private_key(private_pem, password=None)
```

> **Keep `private_key.pem` out of your repo and your shipped artifacts.** Only
> `public_key.pem` belongs in the deployed app. Generated private keys are
> written with `0600` permissions.

---

## 5. Machine fingerprint (HWID)

A client sends you their HWID so you can bind the license to their machine.

```bash
rizmi machine-id            # rich panel
rizmi machine-id --raw      # just the hash (pipe-friendly)
rizmi machine-id --copy     # copy to clipboard
rizmi machine-id --json     # {"hwid","algorithm","platform"}
```

```python
from py_rizmi.core.hwid import HardwareIdentifier
from py_rizmi.integrations.validation import current_hwid

hwid = HardwareIdentifier.get_machine_id()   # SHA-256 hex
hwid = current_hwid()                         # identical convenience wrapper
```

HWID comparison is **case-insensitive**. If you need a custom fingerprint
source, implement the `FingerprintProvider` Protocol and pass it as
`hwid_provider=` to `TrialManager`.

---

## 6. Issuing licenses

### 6.1 CLI

```bash
rizmi license issue \
  --private-key keys/private_key.pem \
  --output license.lic \
  --client "Acme Corp" \
  --license-id "deploy-001" \
  --hwid "<paste-hwid-here>" \
  --features billing --features reports \
  --max-clients 10 \
  --grace-days 14 \
  --exp-days 365
```

All flags of `rizmi license issue`:

| Flag | Default | Notes |
|---|---|---|
| `--private-key` / `-k` | — | Private key PEM (required). |
| `--key-passphrase` | env `RIZMI_KEY_PASSPHRASE` | For an encrypted private key. |
| `--output` / `-o` | `license.lic` | Output `.lic` path. |
| `--client` / `-c` | — | **Required** unless in JSON. |
| `--license-id` / `-i` | — | **Required** unless in JSON. |
| `--hwid` / `-H` | — | **Required** unless in JSON. |
| `--features` / `-f` | `[]` | Repeatable: `--features a --features b`. |
| `--max-clients` / `-m` | `10` | Must be ≥ 0. |
| `--mode` | `offline` | `offline` (or `online`). |
| `--server-url` | `""` | Optional. |
| `--grace-days` / `-g` | `14` | Must be ≥ 0. |
| `--exp-days` / `-e` | `365` | Must be > 0. |
| `--from-json` | — | Path to a JSON spec; explicit flags override file values. `iat`/`exp` from the file are ignored (recomputed). |

```bash
# Issue from a JSON spec
rizmi license issue --private-key keys/private_key.pem --from-json request.json --output license.lic
```

### 6.2 Python — `LicenseIssuer`

```python
from py_rizmi.core.license_issuer import LicenseIssuer
from py_rizmi.models.license_payload import LicensePayload

issuer = LicenseIssuer.from_file("keys/private_key.pem")   # or LicenseIssuer(private_pem)

payload = LicensePayload(
    client="Acme Corp",
    license_id="deploy-001",
    hwid="<client-hwid>",
    features=["billing", "reports"],
    max_clients=10,
    grace_days=14,
)
payload.set_auto_iat()        # iat = now
payload.set_auto_exp(365)     # exp = now + 365 days

token = issuer.issue(payload)            # returns the signed JWT string
path  = issuer.issue_to_file(payload, "license.lic")
```

`LicensePayload` fields:

| Field | Type | Default | Notes |
|---|---|---|---|
| `schema_version` | `int` | `1` | Must be ≥ 0. |
| `client` | `str` | `""` | Required in practice. |
| `license_id` | `str` | `""` | Required in practice. |
| `hwid` | `str` | `""` | Bind to a machine; `""` = unbound. |
| `features` | `list[str]` | `[]` | App-defined feature flags. |
| `max_clients` | `int` | `10` | Must be ≥ 0. |
| `mode` | `str` | `"offline"` | `offline` / `online`. |
| `server_url` | `str` | `""` | Optional. |
| `grace_days` | `int` | `14` | Must be ≥ 0. |
| `iat` | `int` | `0` | Issued-at unix ts. |
| `exp` | `int` | `0` | Expiry unix ts (`0` = never expires). |

Helper methods: `set_auto_iat()`, `set_auto_exp(days=365)`,
`is_expired()`, `is_in_grace()`, `to_dict()`, `from_dict(data)`.

---

## 7. Validating in your app

### 7.1 Direct Python API (recommended — full control, incl. grace)

```python
from py_rizmi.core.license_validator import LicenseValidator, ERROR_MESSAGES

validator = LicenseValidator.from_file("path/to/public_key.pem")

try:
    payload = validator.validate_from_file("path/to/license.lic")
except ValueError as exc:
    reason = str(exc)                       # one of ERROR_MESSAGES keys
    raise SystemExit(ERROR_MESSAGES.get(reason, reason))

print(f"Licensed to {payload.client}; features={payload.features}")
```

`LicenseValidator` members:

| Member | Signature | Notes |
|---|---|---|
| `__init__` | `(public_key: str, clock_guard=None, revocation_list=None)` | `public_key` is a PEM **string**. |
| `from_file` | `from_file(public_key_path, clock_guard=None, revocation_list=None)` | Reads the PEM. |
| `validate` | `validate(token: str, check_hwid: bool = True) -> LicensePayload` | Full pipeline. |
| `validate_from_file` | `validate_from_file(license_path, check_hwid=True) -> LicensePayload` | Raises `missing` if absent. |
| `decode_token` | `decode_token(token) -> dict` | Signature checked, **no** expiry/HWID check. |
| `set_revocation_list` | `set_revocation_list(envelope)` | Install/verify a CRL (see §11). |

Pass `check_hwid=False` only for author-side inspection (e.g. `license inspect`).

### 7.2 Drop-in helper (server-side)

```python
from py_rizmi.integrations.validation import validate_license, ERROR_MESSAGES

try:
    payload = validate_license(
        config_dir="/path/to/app-config",   # must contain public_key.pem + license.lic
        app_name="YourProduct",             # names ClockGuard state dirs (blends in)
        # config=RizmiConfig(...),          # optional centralized config
    )
    print(payload["client"], payload["features"])
except ValueError as exc:
    raise SystemExit(ERROR_MESSAGES.get(str(exc), str(exc)))
```

`validate_license(config_dir, enable_clock_guard=True, app_name="py-rizmi", *, config=None)`
reads `public_key.pem` + `license.lic` from `config_dir` and returns
`payload.to_dict()`. Clock-guard protection is **on by default**.

> **Caveat:** the dict returned by `validate_license` (via `to_dict()`) does
> **not** include the transient `in_grace_period` flag. If you need grace
> detection with the drop-in, use the direct `LicenseValidator` API (§8) so you
> get the `LicensePayload` model back.

---

## 8. Grace period

A license whose `exp` has passed but is still within `exp + grace_days` does
**not** raise — validation succeeds and the model carries `in_grace_period=True`.

```python
from py_rizmi.core.license_validator import LicenseValidator

validator = LicenseValidator.from_file("public_key.pem")
payload = validator.validate_from_file("license.lic")

if payload.in_grace_period:
    warn_user("License expired — running in grace period. Please renew.")
    # or degrade functionality rather than hard-stop

# Model helpers:
payload.is_expired()     # True once exp passed (ignores grace)
payload.is_in_grace()    # True if expired but within grace window
```

If your app must **hard-stop** exactly at `exp` with no grace, check the flag
and treat it as expired yourself (or set `grace_days=0` when issuing).

---

## 9. Error handling

`validate` / `validate_from_file` / `validate_license` raise `ValueError`
whose message is one of these keys. Map to a user message with
`ERROR_MESSAGES.get(reason, reason)`.

| Code | Meaning | Typical fix |
|---|---|---|
| `missing` | No `license.lic` found. | Deliver the license file. |
| `decode_error` | Token can't be decoded (key mismatch). | Wrong `public_key.pem`. |
| `tampered` | Signature invalid / token altered. | Re-issue; investigate tampering. |
| `invalid_algorithm` | Unsupported signing algorithm. | Issue with `RS256`. |
| `unsupported_schema` | `schema_version != 1`. | Upgrade library / re-issue. |
| `expired` | Past `exp + grace_days`. | Renew the license. |
| `hwid_mismatch` | License bound to another machine. | Bind to the correct HWID. |
| `clock_tampering` | System clock rolled back / frozen. | Fix the machine clock. |
| `revoked` | `license_id` on a revocation list. | See §11. |
| `revocation_list_invalid` | CRL envelope has a bad signature. | Publish a correctly signed list. |

```python
from py_rizmi.core.license_validator import ERROR_MESSAGES

try:
    payload = validator.validate_from_file("license.lic")
except ValueError as exc:
    reason = str(exc)
    print("License invalid:", ERROR_MESSAGES.get(reason, reason))
    # reason in {"missing","decode_error","tampered","invalid_algorithm",
    #            "unsupported_schema","expired","hwid_mismatch",
    #            "clock_tampering","revoked","revocation_list_invalid"}
```

---

## 10. Clock-tamper protection

Offline validation can't trust the system clock, so `ClockGuard` persists a
local high-water mark and detects rollback/freeze. It's enabled automatically
by `validate_license` and by `LicenseValidator` when you pass a `clock_guard`.

- State is stored in **three redundant, HMAC-protected, base64-obscured files**
  (one in your `config_dir`, two in OS-standard persistent per-user dirs).
  Deleting any **one** does not disable protection.
- Pass `app_name="YourProduct"` (not `"py-rizmi"`) so the extra dirs blend in
  with your app's own data.
- Disable only for diagnostics/tests: `validate_license(..., enable_clock_guard=False)`
  or `LicenseValidator(public_key, clock_guard=None)`.

A detected rollback raises `ValueError("clock_tampering")`.

---

## 11. License revocation

Publish a **signed revocation list (CRL)** — a JSON envelope
`{"payload": {...}, "signature": "<b64>"}` signed with the *same* private key
as licenses. Validators reject any license whose `license_id` appears on it.

### 11.1 Author side

```python
from py_rizmi.core.revocation import (
    create_revocation_list, sign_revocation_list, RevocationList,
)

payload = create_revocation_list(
    ["L-LEAKED-001", "L-LEAKED-002"],
    next_update_hours=24,          # advisory refresh horizon
)
envelope = sign_revocation_list(payload, private_pem)

# Persist and distribute envelope (e.g. crl.json) to your apps.
import json; open("crl.json","w").write(json.dumps(envelope))
```

```bash
# CLI equivalent (omit LICENSE_IDs to publish a clean / un-revoke list)
rizmi license revoke \
  --private-key keys/private_key.pem \
  --output crl.json \
  --next-update-hours 24 \
  L-LEAKED-001 L-LEAKED-002
```

- `create_revocation_list(revoked_ids, *, next_update_hours=24, issued_at=None)`.
- An **empty** `revoked_ids` list un-revokes everything (publish a fresh clean list).
- `next_update` is **advisory**: offline clients keep using the last known list
  after it passes; `RevocationList.is_stale` lets online apps refuse stale lists.

### 11.2 Validator side

```python
import json
from py_rizmi.core.license_validator import LicenseValidator

envelope = json.load(open("crl.json"))
validator = LicenseValidator.from_file("public_key.pem", revocation_list=envelope)
# or: validator.set_revocation_list(envelope)

payload = validator.validate_from_file("license.lic")   # raises "revoked" if listed
```

A CRL with a **bad signature is rejected loudly** (`revocation_list_invalid`) —
never silently ignored. `verify_revocation_list(data, pub_pem)` returns
`(ok, reason, RevocationList)` where `RevocationList` exposes `is_revoked(id)`
and the `is_stale` property.

---

## 12. Runtime enforcement (long-running apps)

A startup check alone lets an expired license keep running inside a process
that stays up for weeks (servers, workers). `LicenseWatchdog` re-validates on
a timer and fires callbacks on **state changes only**.

```python
from py_rizmi.core.license_validator import LicenseValidator
from py_rizmi.core.runtime_guard import LicenseWatchdog

validator = LicenseValidator.from_file("public_key.pem")

def on_violation(reason, detail):
    server.shutdown()                     # do your shutdown here; watchdog won't kill the process

def on_grace(payload):
    warn("License expired but in grace period — renew soon.")

watchdog = LicenseWatchdog(
    validator,
    "path/to/license.lic",
    interval_seconds=600,                 # re-check every 10 minutes
    on_violation=on_violation,
    on_grace=on_grace,
    strict_start=True,                    # refuse to start on an invalid license
)
watchdog.start()                          # first check runs synchronously
# ... run app ...
watchdog.stop()                           # on shutdown (or use as context manager)
```

`LicenseWatchdog` API:

| Member | Signature / value | Notes |
|---|---|---|
| `__init__` | `(validator, license_path, *, interval_seconds=3600.0, check_hwid=True, on_valid=None, on_grace=None, on_violation=None, strict_start=False)` | `interval_seconds` must be > 0. |
| `start()` / `stop(timeout=5.0)` | methods | `start()` runs one synchronous check first. |
| `check_once()` | `-> bool` | One validation cycle. |
| `is_running` | property | Thread alive? |
| context manager | `with LicenseWatchdog(...) as wd:` | `start()` on enter, `stop()` on exit. |
| `from_config(cls, config, validator, license_path, ...)` | classmethod | Pulls interval/strict-start/check_hwid from `RizmiConfig`. |
| `last_payload` / `last_reason` | attributes | Most recent result. |

`LicenseWatchdogError` (subclass of `RuntimeError`) is raised by `start()` when
`strict_start=True` and the license is already invalid.

`on_violation(reason, detail)` `reason` codes are the §9 keys plus `revoked`
and `missing` (file absent) and `error` (unexpected infra failure, e.g. HWID
backend error). `on_grace(payload)` fires when expired-but-in-grace.

---

## 13. Trial periods (license-free evaluation)

Let clients use your app for `trial_days` without any license file. On first
run the app issues itself a **self-signed trial license** (HWID-bound,
ClockGuard-protected). When the trial ends, block or degrade until they buy a
real `license.lic` — which **always supersedes** the trial, even mid-trial.

```python
from py_rizmi import TrialManager

trial = TrialManager(
    config_dir="path/to/app-config",   # your app's config dir
    trial_days=14,                     # length of evaluation
    public_key=vendor_public_key_pem,  # already embedded for validation
)
status = trial.start_or_check()
if not status.ok:
    ...  # trial expired / tampered / license invalid: block or degrade
```

`TrialStatus.state` is one of:

| State | Meaning |
|---|---|
| `licensed` | A valid real (vendor) license is present. |
| `trial_active` | Trial running; `days_left > 0`. |
| `trial_expired` | Trial over; block / prompt to buy. |
| `tampered` | Trial file fails signature / HWID / clock checks. |
| `no_trial` | No trial started yet (pre-`start_or_check`). |
| `licensed_invalid` | A real license file exists but is invalid — **never** silently falls back to trial. |
| `error` | Unexpected infrastructure failure. |

`status.ok` is `True` for `licensed` / `trial_active`; `status.days_left` is the
remaining days. Other methods: `check()` (no auto-issue), `issue_trial()`,
`from_config(config, config_dir, public_key, ...)`.

### CLI

```bash
rizmi trial status --config-dir ./app-config --public-key vendor_pub.pem [--json]
rizmi trial reset  --config-dir ./app-config --confirm   # diagnostics only; does NOT restart client trial
```

### UI banner

`py_rizmi.gui.widgets.trial_banner.TrialBanner` is a reusable widget (not a
nav tab) you can pin above your app's content, fed a `TrialStatus` via
`update_status(status)`, showing days-left / purchase prompt with an optional
`on_buy` callback.

**Tamper resistance:** editing `trial.lic` → `tampered`; copying another
machine's trial → HWID mismatch → `tampered`; clock rollback → ClockGuard →
`tampered`; deleting `trial.lic` → the original start date is ratcheted into
ClockGuard state, so a new trial inherits it (deletion does **not** reset the
clock).

---

## 14. License swap authorization

Authorize license **replacement** (e.g. a Django backend swapping a user's
license) without ever exposing the private key to the application server. The
client signs a short-lived request locally; the server verifies it.

```python
from py_rizmi import (
    create_swap_request, sign_swap_request, verify_swap_authorization,
)

# 1. App/Server builds a short-lived request
request = create_swap_request(
    current_license="<current-token>",
    new_license="<new-token>",
    valid_minutes=60,
)

# 2. License owner signs locally with the private key (CLI / GUI)
envelope = sign_swap_request(request, private_key_pem)

# 3. Application server verifies
is_valid, reason, verified = verify_swap_authorization(
    authorization_data=envelope,                 # dict or JSON string
    public_key_pem=public_key_pem,
    expected_current_license="<current-token>",
    expected_new_license="<new-token>",
    # expected_request_id="..." optional replay protection
)
if is_valid and verified is not None:
    print("Swap authorized:", verified.request_id)
```

- `create_swap_request(current_license, new_license, request_id=None, valid_minutes=60)`
  → `LicenseSwapPayload`. `valid_minutes` must be > 0.
- `sign_swap_request(payload, private_key_pem, passphrase=None)` →
  `{"payload": {...}, "signature": "<b64>"}`.
- `verify_swap_authorization(data, public_key_pem, expected_current_license,
  expected_new_license, expected_request_id=None, current_time=None)` →
  `(is_valid, reason, LicenseSwapPayload | None)`. **Signature is verified
  first**; reasons include `invalid_signature`, `authorization_expired`,
  `current_license_mismatch`, `new_license_mismatch`, `request_id_mismatch`, etc.

Backward-compatible aliases also exist: `create_replacement_authorization_payload`,
`sign_authorization_payload`, `verify_authorization` (and `ReplacementAuthorizationPayload`
is an alias of `LicenseSwapPayload`).

### CLI

```bash
# Server: create a request
rizmi license create-swap-request \
  --current-license "<cur>" --new-license "<new>" \
  --output swap_request.json --valid-minutes 60

# Owner: sign locally
rizmi license sign-swap \
  --request swap_request.json --private-key keys/private_key.pem \
  --output authorization.rzswap

# Server: verify
rizmi license verify-swap authorization.rzswap \
  --public-key keys/public_key.pem \
  --current-license "<cur>" --new-license "<new>"
```

---

## 15. Centralized configuration (RizmiConfig)

`RizmiConfig` is a **frozen, validated** dataclass — one source of truth for
all py-rizmi components. `RizmiConfig()` reproduces the historical defaults.

| Field | Type | Default | Controls |
|---|---|---|---|
| `trial_days` | `int` | `14` | Trial length (must be > 0). |
| `watchdog_interval_seconds` | `int` | `3600` | `LicenseWatchdog` poll interval (must be > 0). |
| `watchdog_strict_start` | `bool` | `False` | Raise `LicenseWatchdogError` on invalid startup. |
| `watch_trial` | `bool` | `False` | Watchdog trial-supervision flag. |
| `check_hwid` | `bool` | `True` | Enable HWID binding checks. |
| `clock_tolerance_seconds` | `int` | `300` | Clock-guard rollback tolerance (≥ 0). |
| `grace_days` | `int` | `14` | Grace window after `exp` (≥ 0). |
| `max_clients` | `int` | `10` | Default license max seats (must be > 0). |
| `mode` | `str` | `"offline"` | `offline` / `online`. |
| `key_size` | `int` | `2048` | `2048` / `3072` / `4096`. |
| `algorithm` | `str` | `"RS256"` | Only `RS256` supported. |
| `exp_days` | `int` | `365` | Default license validity (must be > 0). |
| `swap_valid_minutes` | `int` | `60` | Swap-auth lifetime (must be > 0). |
| `crl_next_update_hours` | `int` | `24` | CRL advisory refresh horizon (must be > 0). |
| `app_name` | `str` | `"py-rizmi"` | Names the OS dirs for ClockGuard state copies. |

Usage:

```python
from py_rizmi.core.config import RizmiConfig

config = RizmiConfig(trial_days=30, watchdog_interval_seconds=600, grace_days=7)
config = config.replace(exp_days=180)                 # immutable -> new instance
config = RizmiConfig.with_watchdog_interval(hours=10) # convenience setter

# Persist / load
config.to_json("rizmi-config.json")
config = RizmiConfig.from_json("rizmi-config.json")   # ValueError on bad JSON

# Wire it in
validate_license(config_dir, config=config)
TrialManager.from_config(config, config_dir, public_key)
LicenseWatchdog.from_config(config, validator, license_path)
```

Unknown keys in `from_dict`/`from_json` are ignored.

---

## 16. CLI reference

Root command: `rizmi`. Global: `-h/--help`, `--version/-V`. GUI imports are
deferred, so `[gui]` stays optional.

### `rizmi keys`
| Command | Key flags |
|---|---|
| `keys generate` | `--private-out/-p`, `--public-out/-P`, `--key-size/-s` (2048/3072/4096), `--passphrase` |
| `keys inspect <KEY>` | `--key-passphrase` (env `RIZMI_KEY_PASSPHRASE`) |
| `keys verify` | `--private/-p`, `--public/-P` |

### `rizmi license`
| Command | Key flags |
|---|---|
| `license issue` | `--private-key/-k`, `--key-passphrase`, `--output/-o`, `--client/-c`, `--license-id/-i`, `--hwid/-H`, `--features/-f` (repeat), `--max-clients/-m`, `--mode`, `--server-url`, `--grace-days/-g`, `--exp-days/-e`, `--from-json` |
| `license validate <LICENSE>` | `--public-key/-k`, `--no-hwid-check`, `--json` (prints `valid` + `in_grace_period`) |
| `license inspect <LICENSE>` | `--public-key/-k`, `--json` (signature only, not expiry/HWID) |
| `license revoke [LICENSE_ID...]` | `--private-key/-k`, `--key-passphrase`, `--output/-o`, `--next-update-hours` (omit IDs = un-revoke) |
| `license create-swap-request` | `--current-license`, `--new-license`, `--output/-o`, `--request-id`, `--valid-minutes` (60) |
| `license sign-swap` (alias `authorize-replacement`) | `--request/-r`, `--private-key/-k`, `--key-passphrase`, `--output/-o` |
| `license verify-swap <AUTH>` (alias `verify-replacement`) | `--public-key/-k`, `--current-license`, `--new-license`, `--request-id` |

### `rizmi machine-id`
`--raw/-r`, `--copy/-c`, `--json`.

### `rizmi trial`
| Command | Key flags |
|---|---|
| `trial status` | `--config-dir/-c`, `--public-key/-k`, `--days` (14), `--json` |
| `trial reset` | `--config-dir/-c`, `--confirm` (required; diagnostics only) |

### `rizmi gui`
Launches the PyQt6 desktop app (requires `[gui]`); prints a helpful hint and
exits 1 if PyQt6/markdown is missing.

---

## 17. GUI overview

`rizmi gui` opens a sidebar-navigated desktop app with these views:

| View | Purpose |
|---|---|
| **Machine ID** | Display/copy the machine HWID. |
| **Key Management** | Generate / inspect / verify RSA keypairs. |
| **License Generation** | Issue a signed `.lic` from a key + payload. |
| **License Viewer** | Decode / validate / inspect a `.lic`. |
| **License Swap** | Build / sign / verify swap authorizations. |
| **Revocation** | Publish signed revocation lists. |
| **Integration Guide** | Renders the bundled `README.md` (this guide's sibling). |

There is **no "Trial" nav tab** — trial status is surfaced via the `TrialBanner`
widget you embed in your own UI (see §13).

---

## 18. Security & operational caveats

- **Never ship `private_key.pem`.** Only `public_key.pem` belongs in the
  deployed app. Generated private keys are written `0600`.
- **HWID reuse.** HWID is stable per machine; moving a license to another
  machine yields `hwid_mismatch`. Issue per-deployment HWIDs.
- **Clock guard is not encryption.** State files are HMAC-protected and
  obscured, not secret — they raise the bar, not a cryptographic wall.
- **Revocation is advisory-stale.** Offline clients keep honoring the last
  known list past `next_update`; check `RevocationList.is_stale` online.
- **Swap key isolation.** The private key never leaves the owner; the server
  only ever handles signed envelopes.
- **Trial threat model.** Protects against casual/moderate tampering, not a
  determined reverse engineer. Deleting `trial.lic` does not reset the clock.
- **Don't treat offline licensing as piracy protection.** It enforces
  legitimate licensing; it is not DRM.

---

## 19. End-to-end minimal example

**Issuer (build server):**

```python
from py_rizmi.core.license_issuer import LicenseIssuer
from py_rizmi.models.license_payload import LicensePayload
from py_rizmi.integrations.validation import current_hwid   # or ask the client

issuer = LicenseIssuer.from_file("keys/private_key.pem")
payload = LicensePayload(
    client="Acme Corp", license_id="deploy-001",
    hwid=current_hwid(), features=["billing"],
    max_clients=10, grace_days=14,
)
payload.set_auto_iat(); payload.set_auto_exp(365)
issuer.issue_to_file(payload, "license.lic")
# Ship public_key.pem + license.lic to the client.
```

**Integrator (shipped app):**

```python
import sys
from py_rizmi.core.license_validator import LicenseValidator, ERROR_MESSAGES

validator = LicenseValidator.from_file("public_key.pem")
try:
    payload = validator.validate_from_file("license.lic")
except ValueError as exc:
    reason = str(exc)
    print("License invalid:", ERROR_MESSAGES.get(reason, reason))
    sys.exit(1)

if payload.in_grace_period:
    print("Warning: license in grace period — renew soon.")

print(f"Licensed to {payload.client}; features={payload.features}")
```

**Drop-in variant (config dir with `public_key.pem` + `license.lic`):**

```python
from py_rizmi.integrations.validation import validate_license, ERROR_MESSAGES

try:
    data = validate_license(config_dir="./app-config", app_name="YourProduct")
except ValueError as exc:
    print("License invalid:", ERROR_MESSAGES.get(str(exc), str(exc)))
    raise SystemExit(1)
print(data["client"], data["features"])
```

---

## 20. Troubleshooting / FAQ

| Symptom | Code | Cause & fix |
|---|---|---|
| `License invalid: ...decode_error` | `decode_error` | Wrong `public_key.pem` (not the pair used to sign). |
| `License invalid: ...hwid_mismatch` | `hwid_mismatch` | License bound to a different machine; re-issue with the correct HWID. |
| `License invalid: ...clock_tampering` | `clock_tampering` | System clock rolled back/frozen; restore correct time. |
| `License invalid: ...expired` | `expired` | Past `exp + grace_days`; renew. |
| `License invalid: ...tampered` | `tampered` | Token altered or trial file tampered; re-issue. |
| `License invalid: ...missing` | `missing` | `license.lic` not present in `config_dir`. |
| `License invalid: ...revoked` | `revoked` | `license_id` is on the deployed CRL. |
| `revocation_list_invalid` at startup | `revocation_list_invalid` | CRL envelope signature is bad; publish a correctly signed list. |
| Trial resets after deleting `trial.lic` | — | By design: start date is ratcheted into ClockGuard state. |
| `LicenseWatchdogError` at `start()` | — | `strict_start=True` and license already invalid. |
| Can't import PyQt6 after `pip install py-rizmi` | — | GUI is optional; install `py-rizmi[gui]`. |

---

*For public-API stability guarantees, see [`docs/api-stability.md`](api-stability.md).
For architecture decisions, see `docs/adr/`.*
