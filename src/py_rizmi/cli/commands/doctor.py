"""rizmi doctor — one-command health report for an installation.

Run on a client machine (or against a copied-off DB) to answer "why is
licensing failing?" without opening a debugger. Exit 0 when all checks
pass; nonzero with --strict when any check fails.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Annotated, List, Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="doctor",
    help="Diagnose an installation's licensing health.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

_CHECKS: List[dict[str, object]] = []


def _record(name: str, ok: Optional[bool], detail: str) -> None:
    _CHECKS.append({"check": name, "ok": ok, "detail": detail})


@app.command("run")
def doctor_run(
    app_name: Annotated[str, typer.Option("--app-name", "-a", help="Product namespace.")],
    db: Annotated[
        Optional[Path],
        typer.Option("--db", help="StateStore path override."),
    ] = None,
    public_key: Annotated[
        Optional[Path],
        typer.Option("--public-key", "-P", help="Vendor public key PEM for signature checks."),
    ] = None,
    fingerprint: Annotated[
        Optional[str],
        typer.Option("--fingerprint", help="Expected SHA-256 of the public key PEM."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
    strict: Annotated[bool, typer.Option("--strict", help="Exit nonzero on any failure.")] = False,
) -> None:
    """Run all health checks and print the report."""
    from py_rizmi.core.hwid import HardwareIdentifier
    from py_rizmi.core.state_store import StateStore

    del _CHECKS[:]
    machine_id = ""
    try:
        machine_id = HardwareIdentifier.get_machine_id()
        _record("machine-id", True, f"{machine_id[:16]}…")
    except Exception as exc:
        _record("machine-id", False, str(exc))

    # clock sanity: wall vs monotonic drift within tolerance
    wall0, mono0 = time.time(), time.monotonic()
    time.sleep(0.05)
    drift = abs((time.time() - wall0) - (time.monotonic() - mono0))
    _record("clock", drift < 5.0, f"drift {drift:.2f}s")

    resolved_db = Path(db) if db is not None else StateStore.default_path(app_name)
    tampered: List[str] = []
    license_state = "absent"
    try:
        store = StateStore(resolved_db, machine_id=machine_id or "probe",
                           app_name=app_name)
        report = store.verify()
        tampered = list(report.tampered_roles)
        raw = store.active_license_unverified()
        if raw is None:
            trial = store.get("trial:license")
            license_state = "trial_present" if trial else "no_license"
        else:
            license_state = (
                "license_intact" if store.active_license() is not None
                else "license_tampered"
            )
    except Exception as exc:
        _record("state-db", False, f"{resolved_db}: {exc}")
    else:
        _record("state-db", True, str(resolved_db))
        _record(
            "integrity",
            len(tampered) == 0,
            "all rows verified" if not tampered else f"tampered: {', '.join(tampered)}",
        )
        _record("license-state", license_state != "license_tampered", license_state)

    if public_key is not None and fingerprint is not None:
        from py_rizmi.core.keypin import pin_fingerprint

        try:
            pin_fingerprint(public_key.read_text(), fingerprint)
            _record("keypin", True, "public key matches pinned fingerprint")
        except Exception as exc:
            _record("keypin", False, str(exc))
    elif public_key is not None:
        _record("keypin", None, "no --fingerprint given; skipped pin check")

    failed = [c for c in _CHECKS if c["ok"] is False]

    if json_output:
        console.print_json(json.dumps(_CHECKS))
    else:
        table = Table(title=f"rizmi doctor — {app_name}", show_lines=False)
        table.add_column("Check", style="bold")
        table.add_column("Result")
        table.add_column("Detail")
        for c in _CHECKS:
            mark = "[green]✓[/]" if c["ok"] is True else (
                "[yellow]–[/]" if c["ok"] is None else "[red]✗[/]")
            table.add_row(str(c["check"]), mark, str(c["detail"]))
        console.print()
        console.print(table)
        console.print()

    if (strict or fingerprint is not None) and failed:
        # a pinned-fingerprint mismatch is ALWAYS an error, strict or not
        raise typer.Exit(1)
