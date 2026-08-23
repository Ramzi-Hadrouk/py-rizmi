"""rizmi trial — trial period status and management commands."""
from __future__ import annotations

import json
from typing import Annotated

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from py_rizmi.core.trial import TrialManager, TrialStatus

app = typer.Typer(
    name="trial",
    help="License-free trial period management (for integrated apps).",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)

_STATE_STYLES = {
    "licensed": ("bold green", "✓ Licensed"),
    "trial_active": ("bold cyan", "⏳ Trial active"),
    "trial_expired": ("bold red", "✗ Trial expired"),
    "tampered": ("bold red", "✗ Tampered"),
    "licensed_invalid": ("bold yellow", "⚠ License invalid"),
    "no_trial": ("dim", "— No trial started"),
    "error": ("bold red", "✗ Error"),
}


def _error(msg: str) -> None:
    err_console.print(Panel(f"[bold red]✗[/]  {msg}", border_style="red", padding=(0, 1)))


def _render_status(status: TrialStatus) -> Table:
    style, label = _STATE_STYLES.get(status.state, ("white", status.state))
    table = Table(show_header=False, box=box.ROUNDED, padding=(0, 2), border_style="cyan")
    table.add_column(style="bold dim", width=16)
    table.add_column(style="white")
    table.add_row("State", f"[{style}]{label}[/]")
    if status.state == "trial_active":
        table.add_row("Days left", f"[bold cyan]{status.days_left}[/]")
    if status.payload is not None:
        table.add_row("Client", status.payload.client)
        table.add_row("License ID", status.payload.license_id)
        table.add_row("Expires at", str(status.payload.exp))
    if status.detail:
        table.add_row("Detail", status.detail)
    return table


@app.command("status")
def trial_status(
    config_dir: Annotated[
        str,
        typer.Option("--config-dir", "-c", help="App config directory holding trial/license files."),
    ],
    public_key: Annotated[
        str,
        typer.Option("--public-key", "-k", help="Path to the vendor RSA public key PEM."),
    ],
    trial_days: Annotated[
        int,
        typer.Option("--days", help="Trial length in days.", show_default=True),
    ] = 14,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as machine-readable JSON."),
    ] = False,
) -> None:
    """Show trial/licensing state for a config directory.

    This mirrors what an integrated app computes at startup: real license
    first, then the self-signed trial.
    """
    from pathlib import Path

    key_path = Path(public_key)
    if not key_path.exists():
        _error(f"Public key not found: [bold]{key_path}[/]")
        raise typer.Exit(1)

    try:
        manager = TrialManager(
            config_dir=config_dir,
            trial_days=trial_days,
            public_key=key_path.read_text(),
        )
        status = manager.check()
    except ValueError as exc:
        _error(str(exc))
        raise typer.Exit(1) from exc

    if json_output:
        data = {
            "state": status.state,
            "ok": status.ok,
            "days_left": status.days_left,
            "detail": status.detail,
        }
        print(json.dumps(data, indent=2))
        return

    console.print()
    console.print(_render_status(status))
    console.print()
    # Exit code reflects run-permission for scripting.
    raise typer.Exit(code=0 if status.ok else 1)


@app.command("reset")
def trial_reset(
    config_dir: Annotated[
        str,
        typer.Option("--config-dir", "-c", help="App config directory holding trial files."),
    ],
    confirm: Annotated[
        bool,
        typer.Option("--confirm", help="Required. Confirms you understand the implications."),
    ] = False,
) -> None:
    """Remove local trial files (DEVELOPER DIAGNOSTICS ONLY).

    WARNING: on a client machine this does NOT restart the trial — the
    original start date is ratcheted into redundant ClockGuard state
    outside the config dir. This command exists so DEVELOPERS can clean
    their own test machines between runs (where clock-guard ratchets may
    also be removed manually).
    """
    from pathlib import Path

    if not confirm:
        _error(
            "Refusing to reset without [bold]--confirm[/]. Resetting trial "
            "files is a developer diagnostics action."
        )
        raise typer.Exit(1)

    removed = []
    for name in ("trial.lic", "trial_key.pem", "trial_key_pub.pem"):
        p = Path(config_dir) / name
        if p.exists():
            p.unlink()
            removed.append(name)

    if removed:
        console.print(
            Panel(
                f"[bold green]✓[/] Removed: {', '.join(removed)}\n\n"
                "[dim]Note: ClockGuard ratchet state was NOT touched; a new "
                "trial will inherit the original start date unless those "
                "state files are also cleared.[/]",
                border_style="green",
                padding=(0, 1),
            )
        )
    else:
        console.print("[dim]No trial files found.[/]")
