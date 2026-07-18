"""rizmi license — license issuance, validation, and inspection commands."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, List, Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from py_rizmi.core.license_issuer import LicenseIssuer
from py_rizmi.core.license_validator import LicenseValidator
from py_rizmi.models.license_payload import LicensePayload

app = typer.Typer(
    name="license",
    help="License file issuance, validation, and inspection.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


# ─── helpers ─────────────────────────────────────────────────────────────────

def _error(msg: str) -> None:
    err_console.print(Panel(f"[bold red]✗[/]  {msg}", border_style="red", padding=(0, 1)))


def _ts_to_human(ts: int) -> str:
    if ts == 0:
        return "[dim]—[/]"
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def _expiry_status(exp: int) -> Text:
    now = int(time.time())
    if exp == 0:
        return Text("Never", style="dim")
    days_left = (exp - now) // 86_400
    if days_left < 0:
        return Text(f"Expired {abs(days_left)} day(s) ago", style="bold red")
    if days_left <= 14:
        return Text(f"⚠  Expires in {days_left} day(s)", style="bold yellow")
    return Text(f"✓  Expires in {days_left} day(s)", style="bold green")


def _payload_table(payload: LicensePayload) -> Table:
    table = Table(show_header=False, box=box.ROUNDED, padding=(0, 2), border_style="cyan")
    table.add_column(style="bold dim", width=16)
    table.add_column(style="white")
    table.add_row("Schema ver.", f"[dim]v{payload.schema_version}[/]")
    table.add_row("Client", f"[bold cyan]{payload.client}[/]")
    table.add_row("License ID", f"[yellow]{payload.license_id}[/]")
    table.add_row("HWID", f"[dim]{payload.hwid[:24]}…[/]" if len(payload.hwid) > 24 else f"[dim]{payload.hwid}[/]")
    features_str = (
        "  ".join(f"[green]{f}[/]" for f in payload.features)
        if payload.features
        else "[dim]none[/]"
    )
    table.add_row("Features", features_str)
    table.add_row("Max clients", str(payload.max_clients))
    table.add_row("Mode", f"[cyan]{payload.mode}[/]")
    if payload.server_url:
        table.add_row("Server URL", payload.server_url)
    table.add_row("Grace days", str(payload.grace_days))
    table.add_row("Issued at", _ts_to_human(payload.iat))
    table.add_row("Expires at", _ts_to_human(payload.exp))
    table.add_row("Expiry", _expiry_status(payload.exp))
    return table


# ─── commands ────────────────────────────────────────────────────────────────

@app.command("issue")
def license_issue(
    private_key: Annotated[
        Path,
        typer.Option("--private-key", "-k", help="Path to the RSA private key PEM."),
    ],
    key_passphrase: Annotated[
        Optional[str],
        typer.Option(
            "--key-passphrase",
            help="Passphrase for an encrypted private key. Prefer the RIZMI_KEY_PASSPHRASE "
                 "environment variable over this flag — it avoids the passphrase appearing "
                 "in shell history or in `ps` output.",
            envvar="RIZMI_KEY_PASSPHRASE",
        ),
    ] = None,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output path for the .lic file.", show_default=True),
    ] = Path("license.lic"),
    client: Annotated[
        Optional[str],
        typer.Option("--client", "-c", help="Client / company name."),
    ] = None,
    license_id: Annotated[
        Optional[str],
        typer.Option("--license-id", "-i", help="Unique license identifier."),
    ] = None,
    hwid: Annotated[
        Optional[str],
        typer.Option("--hwid", "-H", help="Target machine's hardware ID (from `rizmi machine-id`)."),
    ] = None,
    features: Annotated[
        Optional[List[str]],
        typer.Option("--features", "-f", help="Enabled feature flags (repeatable)."),
    ] = None,
    max_clients: Annotated[
        int,
        typer.Option("--max-clients", "-m", help="Maximum concurrent client seats.", show_default=True),
    ] = 10,
    mode: Annotated[
        str,
        typer.Option("--mode", help='License mode: "offline" or "online".', show_default=True),
    ] = "offline",
    server_url: Annotated[
        str,
        typer.Option("--server-url", help="Validation server URL (online mode only).", show_default=False),
    ] = "",
    grace_days: Annotated[
        int,
        typer.Option("--grace-days", "-g", help="Grace period after expiry (days).", show_default=True),
    ] = 14,
    exp_days: Annotated[
        int,
        typer.Option("--exp-days", "-e", help="License validity in days from today.", show_default=True),
    ] = 365,
) -> None:
    """Issue and sign a new license file (.lic).

    Signs the payload with your RSA private key and writes a JWT token
    to the output file. Deliver the .lic together with your public key
    to the end user.
    """
    # Validate required options (Optional[str] used for mypy compat; Typer shows them without defaults)
    missing = [name for name, val in (("--client", client), ("--license-id", license_id), ("--hwid", hwid)) if val is None]
    if missing:
        _error(f"Missing required option(s): {', '.join(f'[bold]{m}[/]' for m in missing)}")
        raise typer.Exit(1)

    # Narrow types — safe after the check above
    client_val: str = client  # type: ignore[assignment]
    license_id_val: str = license_id  # type: ignore[assignment]
    hwid_val: str = hwid  # type: ignore[assignment]

    if mode not in ("offline", "online"):
        _error(f'Invalid mode [bold]{mode!r}[/]. Choose "offline" or "online".')
        raise typer.Exit(1)

    if not private_key.exists():
        _error(f"Private key not found: [bold]{private_key}[/]")
        raise typer.Exit(1)

    payload = LicensePayload(
        client=client_val,
        license_id=license_id_val,
        hwid=hwid_val,
        features=list(features) if features else [],
        max_clients=max_clients,
        mode=mode,
        server_url=server_url,
        grace_days=grace_days,
    )
    payload.set_auto_iat()
    payload.set_auto_exp(exp_days)

    with console.status("[bold cyan]Signing license…[/]", spinner="dots"):
        try:
            issuer = LicenseIssuer.from_file(str(private_key), passphrase=key_passphrase)
            issuer.issue_to_file(payload, str(output))
        except FileNotFoundError as exc:
            _error(f"Key file error: {exc}")
            raise typer.Exit(2) from exc
        except Exception as exc:
            _error(f"Signing failed: {exc}")
            raise typer.Exit(2) from exc

    console.print()
    console.print(
        Panel(
            f"[bold green]✓[/]  License written to [bold yellow]{output}[/]",
            border_style="green",
            padding=(0, 1),
        )
    )
    console.print(_payload_table(payload))
    console.print()
    console.print(
        "  [dim]📦 Deliver [bold yellow]{out}[/] + your [bold green]public_key.pem[/] to the end user.[/]".format(
            out=output
        )
    )
    console.print()


@app.command("validate")
def license_validate(
    license_path: Annotated[
        Path,
        typer.Argument(metavar="LICENSE", help="Path to the .lic file."),
    ],
    public_key: Annotated[
        Path,
        typer.Option("--public-key", "-k", help="Path to the RSA public key PEM."),
    ],
    no_hwid_check: Annotated[
        bool,
        typer.Option("--no-hwid-check", help="Skip hardware fingerprint verification."),
    ] = False,
) -> None:
    """Validate a license file against the public key and this machine's HWID.

    Checks RSA signature, expiry, and (by default) that the HWID in the
    token matches this machine. Use --no-hwid-check to skip the HWID step,
    which is useful when validating from the author's machine.
    """
    for p in (license_path, public_key):
        if not p.exists():
            _error(f"File not found: [bold]{p}[/]")
            raise typer.Exit(1)

    _ERROR_MESSAGES = {
        "expired": "License has expired.",
        "tampered": "License signature is invalid — the token may have been tampered with.",
        "decode_error": "Token could not be decoded. Check that the public key matches the issuing private key.",
        "hwid_mismatch": "Hardware fingerprint mismatch — this license is not issued for this machine.",
        "missing": "License file not found.",
    }

    with console.status("[bold cyan]Validating license…[/]", spinner="dots"):
        try:
            validator = LicenseValidator.from_file(str(public_key))
            payload = validator.validate_from_file(str(license_path), check_hwid=not no_hwid_check)
        except ValueError as exc:
            reason = str(exc)
            friendly = _ERROR_MESSAGES.get(reason, reason)
            console.print()
            err_console.print(
                Panel(
                    f"[bold red]✗  Validation failed[/]\n\n  {friendly}",
                    border_style="red",
                    padding=(1, 2),
                )
            )
            raise typer.Exit(1) from exc
        except Exception as exc:
            _error(f"Unexpected error: {exc}")
            raise typer.Exit(2) from exc

    hwid_note = "" if not no_hwid_check else "  [dim](HWID check skipped)[/]"
    console.print()
    console.print(
        Panel(
            f"[bold green]✓  License is valid[/]{hwid_note}",
            border_style="green",
            padding=(0, 1),
        )
    )
    console.print(_payload_table(payload))
    console.print()


@app.command("inspect")
def license_inspect(
    license_path: Annotated[
        Path,
        typer.Argument(metavar="LICENSE", help="Path to the .lic file."),
    ],
    public_key: Annotated[
        Path,
        typer.Option("--public-key", "-k", help="Path to the RSA public key PEM."),
    ],
) -> None:
    """Decode and inspect a license file without checking HWID or expiry.

    Useful for license authors who want to inspect tokens they issued.
    Verifies the RSA signature but does NOT check expiry or HWID.
    """
    for p in (license_path, public_key):
        if not p.exists():
            _error(f"File not found: [bold]{p}[/]")
            raise typer.Exit(1)

    with console.status("[bold cyan]Decoding license…[/]", spinner="dots"):
        try:
            token = license_path.read_text().strip()
            validator = LicenseValidator.from_file(str(public_key))
            raw = validator.decode_token(token)
            payload = LicensePayload.from_dict(raw)
        except Exception as exc:
            _error(f"Could not decode license: {exc}")
            raise typer.Exit(2) from exc

    console.print()
    console.print(
        Panel(
            Text("License Inspection", style="bold cyan"),
            border_style="cyan",
            subtitle=f"[dim]{license_path}[/]",
            padding=(0, 1),
        )
    )
    console.print(_payload_table(payload))
    console.print()
