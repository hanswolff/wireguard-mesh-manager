"""Database backup script for migrations.

This script creates a timestamped backup of the SQLite database
before running migrations. This ensures that if a migration fails,
the previous database state can be restored.
"""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

BACKUP_PREFIX = "wireguard_"
DEFAULT_MAX_BACKUPS = 10


def _get_sqlite_related_paths(db_path: Path) -> tuple[Path, Path]:
    """Get WAL and SHM file paths for a SQLite database.

    Args:
        db_path: Path to the database file.

    Returns:
        Tuple of (wal_path, shm_path).
    """
    return (
        db_path.parent / f"{db_path.name}-wal",
        db_path.parent / f"{db_path.name}-shm",
    )


def _copy_sqlite_files(
    source_db: Path,
    target_db: Path,
) -> None:
    """Copy database file along with WAL and SHM if they exist.

    Args:
        source_db: Path to the source database file.
        target_db: Path to the target database file.
    """
    source_wal, source_shm = _get_sqlite_related_paths(source_db)
    target_wal, target_shm = _get_sqlite_related_paths(target_db)

    shutil.copy2(source_db, target_db)

    if source_wal.exists():
        shutil.copy2(source_wal, target_wal)

    if source_shm.exists():
        shutil.copy2(source_shm, target_shm)


def _is_backup_file(path: Path, prefix: str = BACKUP_PREFIX) -> bool:
    """Check if a file is a main database backup file.

    Args:
        path: Path to check.
        prefix: Backup file prefix.

    Returns:
        True if the file is a main backup file (not WAL/SHM).
    """
    return (
        path.is_file()
        and path.name.startswith(prefix)
        and path.name.endswith(".db")
        and not path.name.endswith("-wal")
        and not path.name.endswith("-shm")
    )


def create_db_backup(
    db_path: str | Path = "data/wireguard.db",
    backup_dir: str | Path = "data/backups",
    max_backups: int = DEFAULT_MAX_BACKUPS,
) -> Path:
    """Create a timestamped backup of the database.

    Args:
        db_path: Path to the SQLite database file.
        backup_dir: Directory to store backups.
        max_backups: Maximum number of backups to keep (older ones are deleted).

    Returns:
        Path to the created backup file.

    Raises:
        FileNotFoundError: If the database file doesn't exist.
        ValueError: If max_backups is negative.
        IOError: If the backup operation fails.
    """
    if max_backups < 0:
        raise ValueError("max_backups must be non-negative")

    db_path = Path(db_path)
    backup_dir = Path(backup_dir)

    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")

    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{BACKUP_PREFIX}{timestamp}.db"
    backup_path = backup_dir / backup_filename

    _copy_sqlite_files(db_path, backup_path)

    print(f"Database backup created: {backup_path}")
    _cleanup_old_backups(backup_dir, max_backups)

    return backup_path


def _cleanup_old_backups(
    backup_dir: Path,
    max_backups: int,
    prefix: str = BACKUP_PREFIX,
) -> None:
    """Remove old backups, keeping only the most recent ones.

    Args:
        backup_dir: Directory containing backups.
        max_backups: Maximum number of backups to keep.
        prefix: Filename prefix to identify backup files.
    """
    if max_backups <= 0:
        return

    backup_files = sorted(
        [f for f in backup_dir.glob(f"{prefix}*.db") if _is_backup_file(f, prefix)],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    for old_backup in backup_files[max_backups:]:
        old_backup.unlink()
        print(f"Removed old backup: {old_backup.name}")


def restore_db_backup(
    backup_path: str | Path,
    db_path: str | Path = "data/wireguard.db",
) -> None:
    """Restore the database from a backup file.

    Args:
        backup_path: Path to the backup file to restore.
        db_path: Path where the database should be restored.

    Raises:
        FileNotFoundError: If the backup file doesn't exist.
        IOError: If the restore operation fails.
    """
    backup_path = Path(backup_path)
    db_path = Path(db_path)

    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    db_path.parent.mkdir(parents=True, exist_ok=True)

    wal_path, shm_path = _get_sqlite_related_paths(db_path)

    if wal_path.exists():
        wal_path.unlink()

    if shm_path.exists():
        shm_path.unlink()

    _copy_sqlite_files(backup_path, db_path)

    print(f"Database restored from: {backup_path}")


def list_backups(
    backup_dir: str | Path = "data/backups",
) -> list[Path]:
    """List all database backups.

    Args:
        backup_dir: Directory containing backups.

    Returns:
        List of backup file paths, sorted by modification time (newest first).
    """
    backup_dir = Path(backup_dir)

    if not backup_dir.exists():
        return []

    return sorted(
        [f for f in backup_dir.glob(f"{BACKUP_PREFIX}*.db") if _is_backup_file(f)],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database backup and restore utility")
    subparsers = parser.add_subparsers(dest="command", help="Sub-command")

    # Backup command
    backup_parser = subparsers.add_parser("create", help="Create a database backup")
    backup_parser.add_argument(
        "--db-path",
        default="data/wireguard.db",
        help="Path to the database file (default: data/wireguard.db)",
    )
    backup_parser.add_argument(
        "--backup-dir",
        default="data/backups",
        help="Directory to store backups (default: data/backups)",
    )
    backup_parser.add_argument(
        "--max-backups",
        type=int,
        default=DEFAULT_MAX_BACKUPS,
        help=f"Maximum number of backups to keep (default: {DEFAULT_MAX_BACKUPS})",
    )

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from a backup")
    restore_parser.add_argument(
        "backup_file",
        help="Path to the backup file to restore",
    )
    restore_parser.add_argument(
        "--db-path",
        default="data/wireguard.db",
        help="Path to restore the database to (default: data/wireguard.db)",
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List all backups")
    list_parser.add_argument(
        "--backup-dir",
        default="data/backups",
        help="Directory containing backups (default: data/backups)",
    )

    args = parser.parse_args()

    if args.command == "create":
        create_db_backup(
            db_path=args.db_path,
            backup_dir=args.backup_dir,
            max_backups=args.max_backups,
        )
    elif args.command == "restore":
        restore_db_backup(backup_path=args.backup_file, db_path=args.db_path)
    elif args.command == "list":
        backups = list_backups(backup_dir=args.backup_dir)
        if backups:
            print("Available backups (newest first):")
            for backup in backups:
                mtime = datetime.fromtimestamp(backup.stat().st_mtime, UTC)
                size = backup.stat().st_size
                print(f"  {backup.name} ({mtime.isoformat()}) - {size} bytes")
        else:
            print("No backups found")
    else:
        parser.print_help()
