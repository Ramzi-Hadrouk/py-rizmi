"""rizmi — py-rizmi CLI entry point.

Usage:
    rizmi [OPTIONS] COMMAND [ARGS]...
"""
from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

try:
    from py_rizmi._version import __version__
except ImportError:
    __version__ = "0.0.0.dev0"

from py_rizmi.cli.commands.keys import app as keys_app
from py_rizmi.cli.commands.license_cmd import app as license_app
from py_rizmi.cli.commands.machine_id import app as machine_id_app

console = Console()

# ─── root app ────────────────────────────────────────────────────────────────

app = typer.Typer(
    name="rizmi",
    help="Offline RSA-signed license management — issue, validate, and inspect licenses.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_show_locals=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)

# Register sub-apps
app.add_typer(keys_app,       name="keys",       help="RSA keypair generation and management.")
app.add_typer(license_app,    name="license",    help="License file issuance, validation, and inspection.")
app.add_typer(machine_id_app, name="machine-id", help="Get this machine's hardware fingerprint (HWID).")


# ─── version flag ─────────────────────────────────────────────────────────────

def _version_callback(value: bool) -> None:
    if value:
        _print_banner()
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def root(
    ctx: typer.Context,
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version", "-V",
            help="Show version and exit.",
            callback=_version_callback,
            is_eager=True,
            is_flag=True,
        ),
    ] = None,
) -> None:
    """[bold cyan]rizmi[/] — offline RSA-signed license management.

    Run [bold]rizmi COMMAND --help[/] for detailed usage of any command.
    """
    if ctx.invoked_subcommand is None:
        _print_help()


# ─── custom help / banner ────────────────────────────────────────────────────

def _print_banner() -> None:
    console.print()
    console.print(
        Panel(
            f"[bold cyan]rizmi[/]  [dim]v{__version__}[/]\n"
            "[dim]Offline RSA-signed license management[/]",
            border_style="cyan",
            padding=(1, 4),
            expand=False,
        )
    )
    console.print()


def _print_help() -> None:
    _print_banner()

    table = Table(box=box.SIMPLE, show_header=True, padding=(0, 2))
    table.add_column("[bold]Command[/]", style="bold cyan", no_wrap=True)
    table.add_column("[bold]Description[/]", style="white")

    table.add_row("keys generate",    "Generate a new RSA keypair")
    table.add_row("keys inspect",     "Inspect a PEM key file (type, size, fingerprint)")
    table.add_row("keys verify",      "Verify that a private/public key pair matches")
    table.add_row("",                 "")
    table.add_row("license issue",    "Sign and issue a new .lic license file")
    table.add_row("license validate", "Validate a .lic against public key + this machine's HWID")
    table.add_row("license inspect",  "Decode and inspect a .lic without HWID/expiry check")
    table.add_row("",                 "")
    table.add_row("machine-id",       "Print this machine's hardware fingerprint (HWID)")

    console.print(table)
    console.print(
        "  [dim]Run [bold]rizmi COMMAND --help[/] for full options of any command.[/]"
    )
    console.print()


# ─── entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    app()


if __name__ == "__main__":
    main()
