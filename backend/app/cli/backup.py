"""CLI tool for WireGuard Mesh Manager backup and restore operations."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Annotated

if TYPE_CHECKING:
    from pathlib import Path

import typer

from app.database.connection import AsyncSessionLocal
from app.schemas.export import ExportData
from app.services.export import ExportImportService
from app.utils.encryption import decrypt_data, encrypt_data

# Create CLI app
backup_cli = typer.Typer(
    name="backup",
    help="Backup and restore operations for WireGuard Mesh Manager",
    no_args_is_help=True,
)


@backup_cli.command("create")
def create_backup(
    output_file: Annotated[
        Path, typer.Option("--output", "-o", help="Output backup file path")
    ],
    password: Annotated[
        str,
        typer.Option(
            "--password",
            "-p",
            help="Encryption password",
            prompt=True,
            hide_input=True,
            confirmation_prompt=True,
        ),
    ] = "",
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Optional backup description"),
    ] = None,
    exported_by: Annotated[
        str, typer.Option("--by", "-b", help="Who is creating the backup")
    ] = "cli",
    encrypt: Annotated[
        bool, typer.Option("--encrypt/--no-encrypt", help="Encrypt the backup file")
    ] = True,
) -> None:
    """Create a backup of all networks, locations, and devices.

    Examples:

        # Create an encrypted backup
        backup-cli create -o backup.json

        # Create an unencrypted backup
        backup-cli create -o backup.json --no-encrypt

        # Create backup with description
        backup-cli create -o backup.json -d "Weekly backup"
    """
    if output_file.suffix != ".json":
        typer.echo("Error: Output file must have .json extension", err=True)
        raise typer.Exit(1)

    async def _create_backup() -> None:
        try:
            async with AsyncSessionLocal() as db:
                service = ExportImportService(db)
                export_data = await service.export_networks(
                    exported_by,
                    description,
                    network_ids=None,
                    include_encrypted_keys=True,
                )

                # Convert to JSON string with deterministic ordering
                json_data = json.dumps(
                    export_data.model_dump(), indent=2, default=str, sort_keys=True
                )

                if encrypt:
                    typer.echo("Encrypting backup...")
                    encrypted_content = encrypt_data(json_data, password)
                    final_data = encrypted_content
                else:
                    final_data = export_data.model_dump()

                # Write to file
                output_file.write_text(
                    json.dumps(final_data, indent=2, default=str, sort_keys=True)
                )
                typer.echo(f"✅ Backup created successfully: {output_file}")

                # Show summary
                networks_count = len(export_data.networks)
                devices_count = sum(
                    len(network.devices) for network in export_data.networks
                )
                locations_count = sum(
                    len(network.locations) for network in export_data.networks
                )

                typer.echo(
                    f"📊 Summary: {networks_count} networks, {locations_count} locations, {devices_count} devices"
                )

        except Exception as e:
            typer.echo(f"❌ Error creating backup: {str(e)}", err=True)
            raise typer.Exit(1) from None

    asyncio.run(_create_backup())


@backup_cli.command("restore")
def restore_backup(
    input_file: Annotated[
        Path, typer.Option("--input", "-i", help="Input backup file path")
    ],
    password: Annotated[
        str,
        typer.Option(
            "--password", "-p", help="Decryption password", prompt=True, hide_input=True
        ),
    ] = "",
    overwrite_existing: Annotated[
        bool, typer.Option("--overwrite", help="Overwrite existing networks")
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", help="Show what would be restored without making changes"
        ),
    ] = False,
) -> None:
    """Restore networks, locations, and devices from a backup file.

    Examples:

        # Restore from backup (will prompt for password if needed)
        backup-cli restore -i backup.json

        # Restore and overwrite existing data
        backup-cli restore -i backup.json --overwrite

        # Dry run to see what would be restored
        backup-cli restore -i backup.json --dry-run
    """
    if not input_file.exists():
        typer.echo(f"❌ Error: Backup file not found: {input_file}", err=True)
        raise typer.Exit(1)

    async def _restore_backup() -> None:
        try:
            # Read and parse backup file
            raw_data = json.loads(input_file.read_text())

            # Check if encrypted
            if raw_data.get("encrypted"):
                decrypt_password = password or typer.prompt(
                    "Enter decryption password", hide_input=True
                )
                typer.echo("Decrypting backup...")
                json_data = decrypt_data(raw_data, decrypt_password)
                export_data_dict = json.loads(json_data)
            else:
                export_data_dict = raw_data

            # Validate export data format
            export_data = ExportData.model_validate(export_data_dict)

            if dry_run:
                typer.echo("🔍 DRY RUN - No changes will be made")
                typer.echo(f"📅 Export: {export_data.metadata.exported_at}")
                typer.echo(f"👤 By: {export_data.metadata.exported_by}")
                if export_data.metadata.description:
                    typer.echo(f"📝 Description: {export_data.metadata.description}")

                networks_count = len(export_data.networks)
                devices_count = sum(
                    len(network.devices) for network in export_data.networks
                )
                locations_count = sum(
                    len(network.locations) for network in export_data.networks
                )

                typer.echo(
                    f"📊 Will restore: {networks_count} networks, {locations_count} locations, {devices_count} devices"
                )
                return

            # Perform restore
            async with AsyncSessionLocal() as db:
                service = ExportImportService(db)
                results = await service.import_networks(
                    export_data=export_data,
                    imported_by="cli",
                    overwrite_existing=overwrite_existing,
                )

                # Show results
                typer.echo("✅ Restore completed!")
                typer.echo("📊 Results:")
                typer.echo(f"  Networks created: {results['networks_created']}")
                typer.echo(f"  Networks updated: {results['networks_updated']}")
                typer.echo(f"  Locations created: {results['locations_created']}")
                typer.echo(f"  Devices created: {results['devices_created']}")

                if results["errors"]:
                    typer.echo("❌ Errors:")
                    for error in results["errors"]:
                        typer.echo(f"  • {error}")

        except Exception as e:
            typer.echo(f"❌ Error restoring backup: {str(e)}", err=True)
            raise typer.Exit(1) from None

    asyncio.run(_restore_backup())


@backup_cli.command("info")
def backup_info(
    input_file: Annotated[
        Path, typer.Option("--input", "-i", help="Input backup file path")
    ],
) -> None:
    """Show information about a backup file without restoring it.

    Examples:

        backup-cli info -i backup.json
    """
    if not input_file.exists():
        typer.echo(f"❌ Error: Backup file not found: {input_file}", err=True)
        raise typer.Exit(1)

    try:
        # Read backup file
        raw_data = json.loads(input_file.read_text())

        if raw_data.get("encrypted"):
            typer.echo("🔒 Backup is encrypted")
            # We can only show limited info for encrypted backups without password
            typer.echo(f"📦 Version: {raw_data.get('version', 'Unknown')}")
            typer.echo("📊 Use 'restore --dry-run' with password to see contents")
        else:
            # Parse and show full info
            export_data = ExportData.model_validate(raw_data)

            typer.echo("📋 Backup Information:")
            typer.echo(f"📦 Version: {export_data.metadata.version}")
            typer.echo(f"📅 Exported: {export_data.metadata.exported_at}")
            typer.echo(f"👤 By: {export_data.metadata.exported_by}")
            if export_data.metadata.description:
                typer.echo(f"📝 Description: {export_data.metadata.description}")

            networks_count = len(export_data.networks)
            devices_count = sum(
                len(network.devices) for network in export_data.networks
            )
            locations_count = sum(
                len(network.locations) for network in export_data.networks
            )

            typer.echo("📊 Contents:")
            typer.echo(f"  Networks: {networks_count}")
            typer.echo(f"  Locations: {locations_count}")
            typer.echo(f"  Devices: {devices_count}")

            if export_data.networks:
                typer.echo("🌐 Networks:")
                for network in export_data.networks:
                    device_count = len(network.devices)
                    location_count = len(network.locations)
                    typer.echo(
                        f"  • {network.name} ({network.network_cidr}) - {device_count} devices, {location_count} locations"
                    )

    except json.JSONDecodeError:
        typer.echo("❌ Error: Invalid JSON file", err=True)
        raise typer.Exit(1) from None
    except Exception as e:
        typer.echo(f"❌ Error reading backup: {str(e)}", err=True)
        raise typer.Exit(1) from None


def main() -> None:
    """Entry point for the CLI tool."""
    backup_cli()


if __name__ == "__main__":
    main()
