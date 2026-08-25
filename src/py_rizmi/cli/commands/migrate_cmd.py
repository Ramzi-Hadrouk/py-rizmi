"""rizmi migrate-to-sqlite — one-line upgrade from file-era state."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(
    name="migrate-to-sqlite",
    help="Import file-era trial/licensing state into the SQLite store.",
    no_args_is_help=True,
)
console = Console()


@app.command("run")
def migrate_run(
    config_dir: Annotated[Path, typer.Option("--config-dir", "-c", help="App's legacy config dir.")],
    app_name: Annotated[str, typer.Option("--app-name", "-a", help="Product namespace for the new DB.")],
    db: Annotated[
        Optional[Path],
        typer.Option("--db", help="Target StateStore path (default: per-app platformdirs location)."),
    ] = None,
) -> None:
    """Copy legacy trial key material into the SQLite store (idempotent)."""
    from py_rizmi.core.hwid import HardwareIdentifier
    from py_rizmi.core.state_store import StateStore
    from py_rizmi.core.trial import migrate_legacy_state

    resolved = Path(db) if db is not None else StateStore.default_path(app_name)
    machine_id = HardwareIdentifier.get_machine_id()
    try:
        store_probe = StateStore(resolved, machine_id=machine_id, app_name=app_name)
    except Exception as exc:
        console.print(Panel(f"[red]✗ Cannot open store: {exc}[/]", border_style="red"))
        raise typer.Exit(2) from exc

    if store_probe.get_meta("legacy_migrated"):
        console.print("[yellow]Already migrated — nothing to do.[/]")
        raise typer.Exit(0)

    migrate_legacy_state(config_dir, store_probe)
    console.print()
    console.print(Panel(
        f"[green]✓ Migration complete[/]\n\n"
        f"Store: [bold]{resolved}[/]\n"
        f"Legacy config dir left untouched: {config_dir}",
        border_style="green",
        padding=(0, 2),
    ))
