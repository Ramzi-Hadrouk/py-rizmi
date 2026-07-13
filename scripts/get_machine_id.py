#!/usr/bin/env python3
"""CLI: Print the machine HWID."""
import argparse

from py_rizmi.core.hwid import HardwareIdentifier


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Print the machine hardware ID")
    parser.parse_args()
    print("HWID (SHA-256):", HardwareIdentifier.get_machine_id())
