"""FastAPI integration — protect endpoints with a license dependency.

Run me:
    uvicorn examples.fastapi_dependency:app

A tampered/expired/missing license makes every guarded endpoint return
403 with a human-readable message; a watchdog re-validates in the background.
"""
from __future__ import annotations


from fastapi import Depends, FastAPI, HTTPException

from py_rizmi import LicenseGate, pin_fingerprint

VENDOR_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
...your public key...
-----END PUBLIC KEY-----"""
VENDOR_KEY_FINGERPRINT = "...fingerprint..."

pin_fingerprint(VENDOR_PUBLIC_KEY, VENDOR_KEY_FINGERPRINT)

gate = LicenseGate(
    app_name="MyApi",
    public_key=VENDOR_PUBLIC_KEY,
    config_dir="/var/lib/myapi",
    enable_watchdog=True,
    interval_seconds=600,
    on_violation=lambda reason, detail: print(f"LICENSE VIOLATION: {reason} {detail}"),
)


def require_license():
    status = gate.check()
    if not status:
        raise HTTPException(
            status_code=403,
            detail={"error": "license_invalid", "reason": status.reason,
                    "message": status.message},
        )
    return status


gate.start_watchdog()

app = FastAPI(title="Licensed API")


@app.get("/health")
def health() -> dict:
    """Unlicensed endpoint for load balancers."""
    return {"ok": True}


@app.get("/data", dependencies=[Depends(require_license)])
def data() -> dict:
    return {"rows": [1, 2, 3]}


@app.get("/license")
def license_info() -> dict:
    return gate.status_summary()
