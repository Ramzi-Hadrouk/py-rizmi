"""rizmi app — inspect and manage an installation's licensing.

Point --db at the app's StateStore (default: this machine's per-app
location; pass a copied-off client DB for remote debugging).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from py_rizmi.core.license_gate import LicenseGate

app = typer.Typer(
    name="app",
    help="Inspect and manage an application's licensing state.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


def _build_gate(app_name: str, db: Optional[Path]) -> LicenseGate:
    return LicenseGate(
        app_name=app_name,
        public_key="",  # not needed for store-level ops; validator unused
        config_dir=Path("."),
        db_path=db if db is not None else None,
    )


def _error(msg: str) -> None:
    err_console.print(Panel(f"[bold red]✗[/]  {msg}", border_style="red", padding=(0, 1)))


@app.command("status")
def app_status(
    app_name: Annotated[str, typer.Option("--app-name", "-a", help="Product name (namespace).")],
    db: Annotated[
        Optional[Path],
        typer.Option("--db", help="StateStore path override (e.g. a copied client DB)."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Machine-readable JSON.")] = False,
) -> None:
    """Show license/trial state of an installation."""
    from py_rizmi.core.state_store import StateStore

    resolved = str(db) if db is not None else str(StateStore.default_path(app_name))
    summary = _summary_without_key(app_name, Path(resolved))
    if json_output:
        console.print_json(json.dumps(summary))
        return
    table = Table(show_header=False, box=box.ROUNDED, padding=(0, 2), border_style="cyan")
    table.add_column(style="bold dim", width=14)
    table.add_column(style="white")
    table.add_row("App", app_name)
    table.add_row("DB", resolved)
    for key in ("state", "ok", "days_left", "client", "message"):
        table.add_row(key.capitalize(), str(summary.get(key, "")))
    console.print()
    console.print(table)
    console.print()


def _summary_without_key(app_name: str, db_path: Path) -> dict[str, object]:
    """Store-level report WITHOUT the vendor public key.

    HMAC verification needs the machine binding of the *installation*,
    so this only distinguishes structural states (row present/absent).
    Full validation requires the app itself or `rizmi license validate`.
    """
    from py_rizmi.core.hwid import HardwareIdentifier
    from py_rizmi.core.state_store import StateStore

    store = StateStore(db_path, machine_id=HardwareIdentifier.get_machine_id(),
                       app_name=app_name)
    raw = store.active_license_unverified()
    if raw is None:
        trial = store.get("trial:license")
        if trial:
            return {"state": "trial_present", "ok": True,
                    "message": "Trial data present."}
        return {"state": "no_license", "ok": False,
                "message": "No active license row."}
    verified = store.active_license() is not None
    if not verified:
        return {"state": "licensed_invalid", "ok": False, "reason": "tampered",
                "message": f"Active license '{raw.license_id}' failed integrity check."}
    return {"state": "license_row_present", "ok": None, "license_id": raw.license_id,
            "message": "License row intact; signature/expiry validated inside the app "
                       "(or via `rizmi license validate`)."}


@app.command("activate")
def app_activate(
    app_name: Annotated[str, typer.Option("--app-name", "-a")],
    public_key: Annotated[
        Path, typer.Option("--public-key", "-P", help="Vendor public key PEM (validates before storing).")
    ],
    db: Annotated[Optional[Path], typer.Option("--db")] = None,
    token: Annotated[
        Optional[str],
        typer.Option("--token", help="License JWT ('-' reads it from stdin)."),
    ] = None,
    file: Annotated[Optional[Path], typer.Option("--file", help="Path to license.lic.")] = None,
    machine_id: Annotated[
        Optional[str],
        typer.Option("--machine-id", help="Override machine fingerprint (for foreign DBs)."),
    ] = None,
) -> None:
    """Validate a license against the vendor public key and store it.

    Validation uses the same full chain as the app itself; only valid
    licenses are stored.
    """
    from py_rizmi.core.hwid import HardwareIdentifier
    from py_rizmi.core.license_activator import LicenseActivator
    from py_rizmi.core.state_store import StateStore

    if bool(token) == bool(file):
        _error("Pass exactly one of --token or --file.")
        raise typer.Exit(1)

    resolved = Path(db) if db is not None else StateStore.default_path(app_name)
    try:
        mid = machine_id or HardwareIdentifier.get_machine_id()
        store = StateStore(resolved, machine_id=mid, app_name=app_name)
        activator = LicenseActivator(store, public_key.read_text())
        if token == "-":
            token_text = sys.stdin.readline()
            result = activator.activate_token(token_text)
        elif token is not None:
            result = activator.activate_token(token)
        else:
            assert file is not None
            result = activator.activate_file(file)
    except Exception as exc:
        _error(f"Activation failed: {exc}")
        raise typer.Exit(2) from exc

    if not result.ok:
        _error(f"License rejected: {result.reason} — {result.detail}")
        raise typer.Exit(1)
    console.print("[green]✓[/] License activated.")



@app.command("deactivate")
def app_deactivate(
    app_name: Annotated[str, typer.Option("--app-name", "-a")],
    db: Annotated[Optional[Path], typer.Option("--db")] = None,
    confirm: Annotated[bool, typer.Option("--confirm", help="Required to proceed.")] = False,
) -> None:
    """Archive the active license (keeps history rows)."""
    if not confirm:
        _error("Refusing to deactivate without --confirm.")
        raise typer.Exit(1)
    from py_rizmi.core.state_store import StateStore

    resolved = Path(db) if db is not None else StateStore.default_path(app_name)
    try:
        store = StateStore(resolved, machine_id="probe", app_name=app_name)
    except Exception as exc:
        _error(f"Cannot open store: {exc}")
        raise typer.Exit(2) from exc
    with store._connect() as conn:
        conn.execute("UPDATE licenses SET slot='archived' WHERE slot='active'")
    console.print("[green]✓[/] Active license archived.")
