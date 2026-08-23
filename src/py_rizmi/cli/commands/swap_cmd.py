"""rizmi license swap — authorization signing and verification CLI commands."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel

from py_rizmi.core.swap_auth import (
    create_swap_request,
    sign_swap_request,
    verify_swap_authorization,
)
from py_rizmi.models.swap_payload import LicenseSwapPayload

app = typer.Typer(
    name="swap",
    help="License swap authorization signing and verification.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


def _error(msg: str) -> None:
    err_console.print(Panel(f"[bold red]✗[/]  {msg}", border_style="red", padding=(0, 1)))


@app.command("create-swap-request")
def license_create_swap_request(
    current_license: Annotated[
        Path,
        typer.Option("--current-license", help="Path to the current .lic file."),
    ],
    new_license: Annotated[
        Path,
        typer.Option("--new-license", help="Path to the replacement .lic file."),
    ],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output path for the swap request JSON.", show_default=True),
    ] = Path("swap_request.json"),
    request_id: Annotated[
        Optional[str],
        typer.Option("--request-id", help="Custom request identifier (default: random UUID)."),
    ] = None,
    valid_minutes: Annotated[
        int,
        typer.Option("--valid-minutes", help="How long the resulting authorization may stay valid.", show_default=True),
    ] = 60,
) -> None:
    """Generate a license swap request JSON for the license author to sign.

    Run this on a machine where both license files are available, send the
    output to the author, who signs it with `rizmi license sign-swap`.
    """
    for p in (current_license, new_license):
        if not p.exists():
            _error(f"File not found: [bold]{p}[/]")
            raise typer.Exit(1)
    if valid_minutes <= 0:
        _error(f"--valid-minutes must be positive (got [bold]{valid_minutes}[/]).")
        raise typer.Exit(1)

    try:
        payload = create_swap_request(
            current_license=current_license.read_text().strip(),
            new_license=new_license.read_text().strip(),
            request_id=request_id,
            valid_minutes=valid_minutes,
        )
    except Exception as exc:
        _error(f"Failed to build swap request: {exc}")
        raise typer.Exit(2) from exc

    output.write_text(json.dumps(payload.to_dict(), indent=2))
    console.print()
    console.print(
        Panel(
            f"[bold green]✓[/] Swap request written to [bold yellow]{output}[/]\n\n"
            f"[dim]request_id:[/] {payload.request_id}\n"
            f"[dim]Send this file to the license author for signing.[/]",
            border_style="green",
            padding=(0, 1),
        )
    )
    console.print()


@app.command("sign-swap")
@app.command("authorize-replacement", hidden=True)
def license_sign_swap(
    request_file: Annotated[
        Path,
        typer.Option("--request", "-r", help="Path to swap request JSON file."),
    ],
    private_key: Annotated[
        Path,
        typer.Option("--private-key", "-k", help="Path to RSA private key PEM."),
    ],
    key_passphrase: Annotated[
        Optional[str],
        typer.Option(
            "--key-passphrase",
            help="Passphrase for encrypted private key.",
            envvar="RIZMI_KEY_PASSPHRASE",
        ),
    ] = None,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output path for authorization file (.rzswap / .rzsig).", show_default=True),
    ] = Path("authorization.rzswap"),
) -> None:
    """Sign a license swap request file using your RSA private key."""
    if not request_file.exists():
        _error(f"Request file not found: [bold]{request_file}[/]")
        raise typer.Exit(1)
    if not private_key.exists():
        _error(f"Private key not found: [bold]{private_key}[/]")
        raise typer.Exit(1)

    try:
        data = json.loads(request_file.read_text())
        payload_dict = data.get("payload", data)
        payload = LicenseSwapPayload.from_dict(payload_dict)
        if payload.expires_at <= 0 or payload.expires_at <= payload.issued_at:
            _error(
                "Request file has no valid expiry window (expires_at must be "
                "after issued_at). Swap authorizations are short-lived by "
                "design; refusing to sign a non-expiring authorization."
            )
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as exc:
        _error(f"Failed to parse request file: {exc}")
        raise typer.Exit(1) from exc

    with console.status("[bold cyan]Signing license swap authorization…[/]", spinner="dots"):
        try:
            priv_pem = private_key.read_text()
            auth_output = sign_swap_request(payload, priv_pem, passphrase=key_passphrase)
        except Exception as exc:
            _error(f"Signing failed: {exc}")
            raise typer.Exit(2) from exc

    output.write_text(json.dumps(auth_output, indent=2))
    console.print()
    console.print(
        Panel(
            f"[bold green]✓[/] License swap authorization written to [bold yellow]{output}[/]",
            border_style="green",
            padding=(0, 1),
        )
    )
    console.print()


@app.command("verify-swap")
@app.command("verify-replacement", hidden=True)
def license_verify_swap(
    auth_file: Annotated[
        Path,
        typer.Argument(metavar="AUTH_FILE", help="Path to authorization JSON file (.rzswap / .rzsig)."),
    ],
    public_key: Annotated[
        Path,
        typer.Option("--public-key", "-k", help="Path to RSA public key PEM."),
    ],
    current_license: Annotated[
        Path,
        typer.Option("--current-license", help="Path to current .lic file."),
    ],
    new_license: Annotated[
        Path,
        typer.Option("--new-license", help="Path to replacement .lic file."),
    ],
    expected_request_id: Annotated[
        Optional[str],
        typer.Option(
            "--request-id",
            help="Expect this request_id in the authorization (replay protection: "
                 "fail if the authorization was issued for a different request).",
        ),
    ] = None,
) -> None:
    """Verify a signed license swap authorization file against public key and license contents."""
    for p in (auth_file, public_key, current_license, new_license):
        if not p.exists():
            _error(f"File not found: [bold]{p}[/]")
            raise typer.Exit(1)

    with console.status("[bold cyan]Verifying license swap authorization…[/]", spinner="dots"):
        try:
            auth_data = auth_file.read_text()
            pub_pem = public_key.read_text()
            curr_text = current_license.read_text().strip()
            new_text = new_license.read_text().strip()

            is_valid, reason, _payload = verify_swap_authorization(
                authorization_data=auth_data,
                public_key_pem=pub_pem,
                expected_current_license=curr_text,
                expected_new_license=new_text,
                expected_request_id=expected_request_id,
            )
        except Exception as exc:
            _error(f"Verification error: {exc}")
            raise typer.Exit(2) from exc

    if not is_valid:
        _error(f"License swap authorization invalid: [bold]{reason}[/]")
        raise typer.Exit(1)

    console.print()
    console.print(
        Panel(
            "[bold green]✓  License swap authorization is valid[/]",
            border_style="green",
            padding=(0, 1),
        )
    )
    console.print()


# Backward-compatibility aliases
license_authorize_replacement = license_sign_swap
license_verify_replacement = license_verify_swap
