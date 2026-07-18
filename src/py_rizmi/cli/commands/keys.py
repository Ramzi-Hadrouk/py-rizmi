"""rizmi keys — RSA keypair management commands."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Annotated

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from py_rizmi.core.keypair import KeyPairManager

app = typer.Typer(
    name="keys",
    help="RSA keypair generation and management.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


# ─── helpers ─────────────────────────────────────────────────────────────────

def _error(msg: str) -> None:
    err_console.print(Panel(f"[bold red]✗[/] {msg}", border_style="red", padding=(0, 1)))


def _success(title: str, content: str) -> None:
    console.print(Panel(content, title=f"[bold green]✓  {title}[/]", border_style="green", padding=(1, 2)))


def _load_key_info(path: Path) -> dict[str, str]:
    """Return type + size + fingerprint for any PEM file."""
    pem = path.read_text()
    is_private = "PRIVATE KEY" in pem or "RSA PRIVATE KEY" in pem
    size = KeyPairManager.get_key_size(pem)
    # SHA-256 fingerprint of the raw PEM bytes (portable, no DER conversion needed)
    fingerprint = hashlib.sha256(pem.encode()).hexdigest()
    return {
        "type": "Private Key" if is_private else "Public Key",
        "size": f"{size} bits" if size else "unknown",
        "fingerprint": f"SHA-256:{fingerprint[:16]}…{fingerprint[-8:]}",
        "valid": str(
            KeyPairManager.validate_private_key(pem)
            if is_private
            else KeyPairManager.validate_public_key(pem)
        ),
    }


# ─── commands ────────────────────────────────────────────────────────────────

@app.command("generate")
def keys_generate(
    private_out: Annotated[
        Path,
        typer.Option("--private-out", "-p", help="Output path for the private key PEM.", show_default=True),
    ] = Path("keys/private_key.pem"),
    public_out: Annotated[
        Path,
        typer.Option("--public-out", "-P", help="Output path for the public key PEM.", show_default=True),
    ] = Path("keys/public_key.pem"),
    key_size: Annotated[
        int,
        typer.Option(
            "--key-size",
            "-s",
            help="RSA key size in bits.",
            show_default=True,
        ),
    ] = 2048,
    passphrase: Annotated[
        bool,
        typer.Option(
            "--passphrase",
            help="Encrypt the private key with a passphrase (hidden prompt; "
                 "or set RIZMI_KEY_PASSPHRASE to run non-interactively, e.g. in CI).",
        ),
    ] = False,
) -> None:
    """Generate a new RSA keypair and save both keys to disk.

    Private key is saved with mode 0o600 (owner read/write only).
    Supported key sizes: 2048, 3072, 4096.
    """
    if key_size not in KeyPairManager.KEY_SIZES:
        _error(f"Unsupported key size [bold]{key_size}[/]. Choose from: {KeyPairManager.KEY_SIZES}")
        raise typer.Exit(1)

    pw: str | None = None
    if passphrase:
        pw = os.environ.get("RIZMI_KEY_PASSPHRASE") or typer.prompt(
            "Private key passphrase", hide_input=True, confirmation_prompt=True
        )

    with console.status(
        f"[bold cyan]Generating {key_size}-bit RSA keypair…[/]", spinner="dots"
    ):
        try:
            KeyPairManager.save_keypair(str(private_out), str(public_out), key_size, passphrase=pw)
        except Exception as exc:
            _error(f"Key generation failed: {exc}")
            raise typer.Exit(2) from exc

    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    table.add_column(style="dim")
    table.add_column(style="bold white")
    table.add_row("Key size", f"[cyan]{key_size}[/] bits")
    table.add_row("Private key", f"[yellow]{private_out}[/]  [dim](chmod 0600)[/]")
    table.add_row("Public key", f"[green]{public_out}[/]")

    _success("Keypair generated", "")
    console.print(table)
    console.print()
    console.print(
        "  [dim]🔒 Keep [bold yellow]private_key.pem[/] secret — never commit or share it.[/]"
    )


@app.command("inspect")
def keys_inspect(
    key: Annotated[
        Path,
        typer.Argument(help="Path to a .pem key file (private or public)."),
    ],
) -> None:
    """Inspect a PEM key file — show type, size, and fingerprint."""
    if not key.exists():
        _error(f"File not found: [bold]{key}[/]")
        raise typer.Exit(1)

    try:
        info = _load_key_info(key)
    except Exception as exc:
        _error(f"Could not read key: {exc}")
        raise typer.Exit(2) from exc

    valid_icon = "[green]✓ valid[/]" if info["valid"] == "True" else "[red]✗ invalid[/]"

    table = Table(show_header=False, box=box.ROUNDED, padding=(0, 2), border_style="cyan")
    table.add_column(style="bold dim", width=16)
    table.add_column(style="white")
    table.add_row("File", str(key))
    table.add_row("Type", f"[cyan]{info['type']}[/]")
    table.add_row("Size", f"[yellow]{info['size']}[/]")
    table.add_row("Fingerprint", f"[dim]{info['fingerprint']}[/]")
    table.add_row("Status", valid_icon)

    console.print()
    console.print(table)
    console.print()


@app.command("verify")
def keys_verify(
    private: Annotated[
        Path,
        typer.Option("--private", "-p", help="Path to the private key PEM."),
    ],
    public: Annotated[
        Path,
        typer.Option("--public", "-P", help="Path to the public key PEM."),
    ],
) -> None:
    """Verify that a private key and public key form a matching pair."""
    for p in (private, public):
        if not p.exists():
            _error(f"File not found: [bold]{p}[/]")
            raise typer.Exit(1)

    try:
        priv_pem = private.read_text()
        pub_pem = public.read_text()
        match = KeyPairManager.verify_keypair(priv_pem, pub_pem)
        priv_size = KeyPairManager.get_key_size(priv_pem)
        pub_size = KeyPairManager.get_key_size(pub_pem)
    except Exception as exc:
        _error(f"Could not read keys: {exc}")
        raise typer.Exit(2) from exc

    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    table.add_column(style="dim")
    table.add_column(style="white")
    table.add_row("Private key", f"[yellow]{private}[/]  [dim]({priv_size} bits)[/]")
    table.add_row("Public key", f"[green]{public}[/]  [dim]({pub_size} bits)[/]")

    if match:
        result = Text("✓  Keys are a matching pair", style="bold green")
        border = "green"
    else:
        result = Text("✗  Keys do NOT match", style="bold red")
        border = "red"

    console.print()
    console.print(table)
    console.print(Panel(result, border_style=border, padding=(0, 2)))
    console.print()

    if not match:
        raise typer.Exit(1)
