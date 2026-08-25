"""rizmi license — license issuance, validation, and inspection commands."""
from __future__ import annotations

import json
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
from py_rizmi.core.license_validator import ERROR_MESSAGES, LicenseValidator
from py_rizmi.core.revocation import (
    create_revocation_list,
    sign_revocation_list,
)
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


def _emit_json(data: dict[str, object]) -> None:
    """Print *data* as machine-readable JSON on stdout (no Rich markup)."""
    console.print_json(json.dumps(data, indent=2))


def _ts_to_human(ts: int) -> str:
    if ts == 0:
        return "[dim]—[/]"
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def _expiry_status(payload: LicensePayload) -> Text:
    now = int(time.time())
    if payload.exp == 0:
        return Text("Never", style="dim")
    
    if payload.in_grace_period:
        effective_exp = payload.exp + (payload.grace_days * 86_400)
        grace_left = (effective_exp - now) // 86_400
        return Text(f"⚠  Expired, in grace period ({grace_left} day(s) left)", style="bold yellow")

    days_left = (payload.exp - now) // 86_400
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
    table.add_row("Expiry", _expiry_status(payload))
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
    from_json: Annotated[
        Optional[Path],
        typer.Option(
            "--from-json",
            help="Read the payload spec (client, license_id, hwid, features, ...) "
                 "from a JSON file instead of individual flags. Explicit flags "
                 "still override values from the file; iat/exp in the file are "
                 "ignored (always computed from --exp-days).",
        ),
    ] = None,
) -> None:
    """Issue and sign a new license file (.lic).

    Signs the payload with your RSA private key and writes a JWT token
    to the output file. Deliver the .lic together with your public key
    to the end user.
    """
    # Validate required options (Optional[str] used for mypy compat; Typer shows them without defaults)
    if from_json is not None:
        try:
            spec = json.loads(from_json.read_text())
            if not isinstance(spec, dict):
                raise ValueError("JSON root must be an object")
        except Exception as exc:
            _error(f"Could not read payload spec {from_json}: {exc}")
            raise typer.Exit(1) from exc
        client = client if client is not None else spec.get("client")
        license_id = license_id if license_id is not None else spec.get("license_id")
        hwid = hwid if hwid is not None else spec.get("hwid")
        features = features if features else spec.get("features")
        max_clients = max_clients if max_clients != 10 else int(spec.get("max_clients", 10))
        mode = mode if mode != "offline" else str(spec.get("mode", "offline"))
        server_url = server_url or str(spec.get("server_url", ""))
        grace_days = grace_days if grace_days != 14 else int(spec.get("grace_days", 14))

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

    if exp_days <= 0:
        _error(f"--exp-days must be positive (got [bold]{exp_days}[/]).")
        raise typer.Exit(1)
    if grace_days < 0:
        _error(f"--grace-days must be non-negative (got [bold]{grace_days}[/]).")
        raise typer.Exit(1)
    if max_clients < 1:
        _error(f"--max-clients must be at least 1 (got [bold]{max_clients}[/]).")
        raise typer.Exit(1)
    if mode == "online" and not server_url:
        _error('--server-url is required when --mode is "online".')
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


@app.command("revoke")
def license_revoke(
    private_key: Annotated[
        Path,
        typer.Option("--private-key", "-k", help="Path to the RSA private key PEM."),
    ],
    license_ids: Annotated[
        Optional[List[str]],
        typer.Argument(metavar="LICENSE_ID", help="License ID(s) to revoke. Omit to publish a clean (un-revoke) list."),
    ] = None,
    key_passphrase: Annotated[
        Optional[str],
        typer.Option(
            "--key-passphrase",
            help="Passphrase for an encrypted private key (or set RIZMI_KEY_PASSPHRASE).",
            envvar="RIZMI_KEY_PASSPHRASE",
        ),
    ] = None,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output path for the signed CRL JSON.", show_default=True),
    ] = Path("revocation_list.json"),
    next_update_hours: Annotated[
        int,
        typer.Option(
            "--next-update-hours",
            help="Advisory refresh horizon embedded in the list.",
            show_default=True,
        ),
    ] = 24,
) -> None:
    """Publish a signed revocation list revoking the given license ID(s).

    Distribute the output file to your apps and pass it to
    LicenseValidator(revocation_list=...) — any license whose ID is on
    the list will fail validation with 'revoked'. Re-publish with an
    empty ID list to un-revoke everything.
    """
    if next_update_hours <= 0:
        _error(f"--next-update-hours must be positive (got [bold]{next_update_hours}[/]).")
        raise typer.Exit(1)
    if not private_key.exists():
        _error(f"Private key not found: [bold]{private_key}[/]")
        raise typer.Exit(1)

    cleaned = [lid.strip() for lid in (license_ids or []) if lid.strip()]
    try:
        payload = create_revocation_list(cleaned, next_update_hours=next_update_hours)
        envelope = sign_revocation_list(payload, private_key.read_text(), passphrase=key_passphrase)
    except Exception as exc:
        _error(f"Revocation list signing failed: {exc}")
        raise typer.Exit(2) from exc

    output.write_text(json.dumps(envelope, indent=2))
    console.print()
    console.print(
        Panel(
            f"[bold green]✓[/] Signed revocation list written to [bold yellow]{output}[/]\n\n"
            f"[dim]Revoked IDs:[/] {', '.join(cleaned) if cleaned else '[i]none (clean list)[/]'}\n"
            f"[dim]Next update:[/] {_ts_to_human(payload['next_update'])}\n\n"
            f"[dim]Distribute this file; validators reject listed licenses with 'revoked'.[/]",
            border_style="green",
            padding=(0, 1),
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
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output the payload as machine-readable JSON."),
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

    with console.status("[bold cyan]Validating license…[/]", spinner="dots"):
        try:
            validator = LicenseValidator.from_file(str(public_key))
            payload = validator.validate_from_file(str(license_path), check_hwid=not no_hwid_check)
        except ValueError as exc:
            reason = str(exc)
            friendly = ERROR_MESSAGES.get(reason, reason)
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
    if json_output:
        data = payload.to_dict()
        data["valid"] = True
        data["in_grace_period"] = payload.in_grace_period
        _emit_json(data)
        return
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
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output the payload as machine-readable JSON."),
    ] = False,
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
    if json_output:
        _emit_json(payload.to_dict())
        return
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


