"""rizmi init — scaffold a licensing setup for a new product."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(
    name="init",
    help="Generate keys + a paste-ready LicenseGate snippet for a new product.",
    no_args_is_help=True,
)
console = Console()

_SNIPPET = '''\
from py_rizmi import LicenseGate, pin_fingerprint

VENDOR_PUBLIC_KEY = """{pub_pem}"""          # compiled into your binary
VENDOR_KEY_FINGERPRINT = "{fingerprint}"

pin_fingerprint(VENDOR_PUBLIC_KEY, VENDOR_KEY_FINGERPRINT)   # startup gate

gate = LicenseGate(
    app_name="{app_name}",
    public_key=VENDOR_PUBLIC_KEY,
    expected_fingerprint=VENDOR_KEY_FINGERPRINT,
    config_dir="~/.config/{app_name}",
)

status = gate.start()            # first run starts the trial
if not status:
    print(status.message)       # expired / tampered / ...
'''


@app.command("run")
def init_run(
    app_name: Annotated[str, typer.Argument(help="Product name (used as namespace).")],
    out: Annotated[
        Optional[Path],
        typer.Option("--out", "-o", help="Output dir for keys."),
    ] = None,
    key_size: Annotated[int, typer.Option("--key-size", "-s")] = 2048,
) -> None:
    """Generate a keypair and print your integration snippet."""
    from py_rizmi.core.keypin import key_fingerprint

    out_dir = out if out is not None else Path("licensing")
    priv_path = out_dir / "private_key.pem"
    pub_path = out_dir / "public_key.pem"

    if priv_path.exists() or pub_path.exists():
        console.print(Panel(
            f"[red]✗ Refusing to overwrite existing keys in {out_dir}.[/]",
            border_style="red",
        ))
        raise typer.Exit(1)

    from py_rizmi.core.keypair import KeyPairManager

    KeyPairManager.save_keypair(str(priv_path), str(pub_path), key_size=key_size)
    try:
        os.chmod(priv_path, 0o600)
    except OSError:
        pass
    pub_pem = pub_path.read_text()
    fingerprint = key_fingerprint(pub_pem)

    snippet = _SNIPPET.format(
        pub_pem=pub_pem.strip(), fingerprint=fingerprint, app_name=app_name
    )
    console.print()
    console.print(Panel(
        f"[green]✓ Keys written:[/] {priv_path} , {pub_path}\n\n"
        f"Next steps:\n"
        f"  1. Paste the snippet below into your app source.\n"
        f"  2. Compile (Nuitka keeps constants safe).\n"
        f"  3. Issue licenses: rizmi license issue --private-key {priv_path} ...\n"
        f"  4. Health-check any install: rizmi doctor --app-name {app_name}",
        title=f"py-rizmi ready for '{app_name}'",
        border_style="green",
        padding=(0, 2),
    ))
    console.print()
    console.print(f"[dim]Public-key fingerprint:[/] [bold]{fingerprint}[/]")
    console.print()
    console.print(snippet)
