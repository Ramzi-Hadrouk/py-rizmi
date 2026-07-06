#!/usr/bin/env python3
"""CLI: Generate an RSA signing keypair (Task 4.2)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core.keypair import KeyPairManager


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate RSA signing keypair")
    parser.add_argument("--private-out", default="keys/private_key.pem")
    parser.add_argument("--public-out", default="keys/public_key.pem")
    parser.add_argument("--key-size", type=int, default=2048)
    args = parser.parse_args()

    KeyPairManager.save_keypair(args.private_out, args.public_out, args.key_size)
    print(f"Private key: {args.private_out}")
    print(f"Public key:  {args.public_out}")
