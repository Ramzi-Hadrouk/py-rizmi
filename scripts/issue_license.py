#!/usr/bin/env python3
"""CLI: Issue a signed license token (Task 4.4)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.license_issuer import LicenseIssuer
from src.core.license_token import LicensePayload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Issue a license token")
    parser.add_argument("--private-key", required=True)
    parser.add_argument("--output", default="license.lic")
    parser.add_argument("--client", required=True)
    parser.add_argument("--license-id", required=True)
    parser.add_argument("--hwid", required=True)
    parser.add_argument("--features", nargs="*", default=["billing", "reports"])
    parser.add_argument("--max-clients", type=int, default=10)
    parser.add_argument("--mode", choices=["offline", "online"], default="offline")
    parser.add_argument("--server-url", default="")
    parser.add_argument("--grace-days", type=int, default=14)
    parser.add_argument("--exp-days", type=int, default=365)
    args = parser.parse_args()

    payload = LicensePayload(
        client=args.client,
        license_id=args.license_id,
        hwid=args.hwid,
        features=args.features,
        max_clients=args.max_clients,
        mode=args.mode,
        server_url=args.server_url,
        grace_days=args.grace_days,
    )
    payload.set_auto_iat()
    payload.set_auto_exp(args.exp_days)

    issuer = LicenseIssuer.from_file(args.private_key)
    issuer.issue_to_file(payload, args.output)
    print(f"License written to {args.output}")
