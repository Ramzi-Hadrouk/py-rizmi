"""rizmi machine-id — hardware fingerprint command."""
from __future__ import annotations

import subprocess
import sys
from typing import Annotated

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from py_rizmi.core.hwid import HardwareIdentifier, MachineIdError

app = typer.Typer(
    name="machine-id",
    help="Get this machine's hardware fingerprint (HWID).",
    invoke_without_command=True,
)
console = Console()
err_console = Console(stderr=True)


def _copy_to_clipboard(text: str) -> bool:
    """Attempt to copy *text* to the system clipboard. Returns True on success."""
    # Try xclip (Linux X11)
    for cmd in (["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"], ["pbcopy"]):
        try:
            proc = subprocess.run(cmd, input=text.encode(), capture_output=True, timeout=3)
            if proc.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    # Fallback: pyperclip if installed
    try:
        import pyperclip  # type: ignore[import]
        pyperclip.copy(text)
        return True
    except Exception:
        pass
    return False


@app.callback(invoke_without_command=True)
def machine_id(
    raw: Annotated[
        bool,
        typer.Option("--raw", "-r", help="Print only the HWID hash (for piping)."),
    ] = False,
    copy: Annotated[
        bool,
        typer.Option("--copy", "-c", help="Copy the HWID to the system clipboard."),
    ] = False,
) -> None:
    """Get this machine's hardware fingerprint (HWID).

    The HWID is a SHA-256 hash of the OS-level machine identifier
    (stable across reboots, survives most hardware changes).

    Send this value to your license author to obtain a machine-bound license.
    """
    try:
        hwid = HardwareIdentifier.get_machine_id()
    except MachineIdError as exc:
        err_console.print(
            Panel(
                f"[bold red]✗  Could not read machine ID[/]\n\n  {exc}",
                border_style="red",
                padding=(1, 2),
            )
        )
        raise typer.Exit(2) from exc

    if raw:
        # Plain output for piping: `rizmi machine-id --raw | pbcopy`
        print(hwid)
        return

    if copy:
        success = _copy_to_clipboard(hwid)
        copied_note = (
            "[green]  ✓ Copied to clipboard![/]"
            if success
            else "[yellow]  ⚠  Could not copy — install xclip or xsel[/]"
        )
    else:
        copied_note = ""

    table = Table(show_header=False, box=box.ROUNDED, padding=(0, 2), border_style="cyan")
    table.add_column(style="bold dim", width=12)
    table.add_column(style="white")

    platform_info = sys.platform
    table.add_row("Platform", f"[dim]{platform_info}[/]")
    table.add_row("Algorithm", "[dim]SHA-256[/]")
    table.add_row("HWID", f"[bold yellow]{hwid}[/]")

    console.print()
    console.print(
        Panel(
            "[bold]Machine Hardware ID[/]",
            border_style="cyan",
            padding=(0, 1),
        )
    )
    console.print(table)

    if copied_note:
        console.print(f"\n{copied_note}")

    console.print()
    console.print(
        "  [dim]📋 Send this HWID to your license author to receive a machine-bound license.[/]"
    )
    console.print()
