"""Tests for database backup script."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts import db_backup


class TestSqliteRelatedPaths:
    """Test cases for _get_sqlite_related_paths helper function."""

    def test_get_sqlite_related_paths(self):
        """Test getting WAL and SHM file paths."""
        db_path = Path("/data/test.db")

        wal_path, shm_path = db_backup._get_sqlite_related_paths(db_path)

        assert wal_path == Path("/data/test.db-wal")
        assert shm_path == Path("/data/test.db-shm")

    def test_get_sqlite_related_paths_nested(self):
        """Test getting WAL and SHM paths for nested database."""
        db_path = Path("/some/long/path/to/database.db")

        wal_path, shm_path = db_backup._get_sqlite_related_paths(db_path)

        assert wal_path == Path("/some/long/path/to/database.db-wal")
        assert shm_path == Path("/some/long/path/to/database.db-shm")


class TestIsBackupFile:
    """Test cases for _is_backup_file helper function."""

    def test_is_backup_file_valid(self, tmp_path: Path):
        """Test identifying a valid backup file."""
        backup_file = tmp_path / "wireguard_20251230_120000.db"
        backup_file.touch()

        assert db_backup._is_backup_file(backup_file) is True

    def test_is_backup_file_wal(self, tmp_path: Path):
        """Test that WAL files are not considered backup files."""
        wal_file = tmp_path / "wireguard_20251230_120000.db-wal"
        wal_file.touch()

        assert db_backup._is_backup_file(wal_file) is False

    def test_is_backup_file_shm(self, tmp_path: Path):
        """Test that SHM files are not considered backup files."""
        shm_file = tmp_path / "wireguard_20251230_120000.db-shm"
        shm_file.touch()

        assert db_backup._is_backup_file(shm_file) is False

    def test_is_backup_file_wrong_prefix(self, tmp_path: Path):
        """Test that files with wrong prefix are not considered backups."""
        other_file = tmp_path / "other_20251230_120000.db"
        other_file.touch()

        assert db_backup._is_backup_file(other_file) is False

    def test_is_backup_file_custom_prefix(self, tmp_path: Path):
        """Test with custom prefix."""
        custom_file = tmp_path / "custom_20251230_120000.db"
        custom_file.touch()

        assert db_backup._is_backup_file(custom_file, prefix="custom_") is True
        assert db_backup._is_backup_file(custom_file) is False


class TestCreateDbBackup:
    """Test cases for create_db_backup function."""

    def test_create_db_backup_basic(self, tmp_path: Path):
        """Test creating a basic database backup."""
        db_file = tmp_path / "test.db"
        db_file.write_text("test data")

        backup_dir = tmp_path / "backups"
        backup_path = db_backup.create_db_backup(
            db_path=db_file, backup_dir=backup_dir, max_backups=3
        )

        assert backup_path.exists()
        assert backup_path.name.startswith("wireguard_")
        assert backup_path.name.endswith(".db")
        assert backup_path.read_text() == "test data"
        assert backup_path.parent == backup_dir

    def test_create_db_backup_with_wal_and_shm(self, tmp_path: Path):
        """Test creating backup with WAL and SHM files."""
        db_file = tmp_path / "test.db"
        db_file.write_text("db data")

        wal_file = tmp_path / "test.db-wal"
        wal_file.write_text("wal data")

        shm_file = tmp_path / "test.db-shm"
        shm_file.write_text("shm data")

        backup_dir = tmp_path / "backups"
        backup_path = db_backup.create_db_backup(db_path=db_file, backup_dir=backup_dir)

        backup_wal = backup_dir / f"{backup_path.name}-wal"
        backup_shm = backup_dir / f"{backup_path.name}-shm"

        assert backup_wal.exists()
        assert backup_shm.exists()
        assert backup_wal.read_text() == "wal data"
        assert backup_shm.read_text() == "shm data"

    def test_create_db_backup_only_wal(self, tmp_path: Path):
        """Test creating backup with only WAL file (no SHM)."""
        db_file = tmp_path / "test.db"
        db_file.write_text("db data")

        wal_file = tmp_path / "test.db-wal"
        wal_file.write_text("wal data")

        backup_dir = tmp_path / "backups"
        backup_path = db_backup.create_db_backup(db_path=db_file, backup_dir=backup_dir)

        backup_wal = backup_dir / f"{backup_path.name}-wal"
        backup_shm = backup_dir / f"{backup_path.name}-shm"

        assert backup_wal.exists()
        assert not backup_shm.exists()

    def test_create_db_backup_nonexistent_db(self, tmp_path: Path):
        """Test that creating backup for nonexistent database raises error."""
        db_file = tmp_path / "nonexistent.db"
        backup_dir = tmp_path / "backups"

        with pytest.raises(FileNotFoundError, match="Database file not found"):
            db_backup.create_db_backup(db_path=db_file, backup_dir=backup_dir)

    def test_create_db_backup_negative_max_backups(self, tmp_path: Path):
        """Test that negative max_backups raises ValueError."""
        db_file = tmp_path / "test.db"
        db_file.write_text("data")
        backup_dir = tmp_path / "backups"

        with pytest.raises(ValueError, match="max_backups must be non-negative"):
            db_backup.create_db_backup(
                db_path=db_file, backup_dir=backup_dir, max_backups=-1
            )

    def test_create_db_backup_cleanup_old(self, tmp_path: Path):
        """Test that old backups are cleaned up."""
        import os

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        base_time = datetime(2025, 12, 30, 12, 0, 0, tzinfo=UTC)

        # Create backups manually with different timestamps
        for i in range(5):
            backup_path = (
                backup_dir
                / f"wireguard_{(base_time + timedelta(seconds=i)).strftime('%Y%m%d_%H%M%S')}.db"
            )
            backup_path.write_text(f"backup_{i}")
            mtime = (base_time + timedelta(seconds=i)).timestamp()
            os.utime(backup_path, (mtime, mtime))

        # Manually trigger cleanup
        db_backup._cleanup_old_backups(backup_dir, max_backups=3)

        backups = db_backup.list_backups(backup_dir)
        assert len(backups) == 3

    def test_create_db_backup_max_backups_zero(self, tmp_path: Path, capsys):
        """Test that max_backups=0 does not delete any backups."""
        db_file = tmp_path / "test.db"
        db_file.write_text("data")
        backup_dir = tmp_path / "backups"

        db_backup.create_db_backup(
            db_path=db_file, backup_dir=backup_dir, max_backups=0
        )
        captured = capsys.readouterr()

        assert "Removed old backup:" not in captured.out

    def test_create_db_backup_creates_backup_dir(self, tmp_path: Path):
        """Test that backup directory is created if it doesn't exist."""
        db_file = tmp_path / "test.db"
        db_file.write_text("data")
        backup_dir = tmp_path / "deeply" / "nested" / "backups"

        assert not backup_dir.exists()

        db_backup.create_db_backup(db_path=db_file, backup_dir=backup_dir)

        assert backup_dir.exists()


class TestRestoreDbBackup:
    """Test cases for restore_db_backup function."""

    def test_restore_db_backup_basic(self, tmp_path: Path):
        """Test basic database restore."""
        # Create backup
        backup_file = tmp_path / "wireguard_20251230_120000.db"
        backup_file.write_text("backup data")

        # Restore to different location
        db_file = tmp_path / "restored.db"
        db_backup.restore_db_backup(backup_path=backup_file, db_path=db_file)

        assert db_file.exists()
        assert db_file.read_text() == "backup data"

    def test_restore_db_backup_with_wal_and_shm(self, tmp_path: Path):
        """Test restoring with WAL and SHM files."""
        # Create backup with WAL and SHM
        backup_file = tmp_path / "backups" / "wireguard_20251230_120000.db"
        backup_file.parent.mkdir()
        backup_file.write_text("db data")

        backup_wal = tmp_path / "backups" / "wireguard_20251230_120000.db-wal"
        backup_wal.write_text("wal data")

        backup_shm = tmp_path / "backups" / "wireguard_20251230_120000.db-shm"
        backup_shm.write_text("shm data")

        # Restore
        db_file = tmp_path / "restored.db"
        db_backup.restore_db_backup(backup_path=backup_file, db_path=db_file)

        restored_wal = tmp_path / "restored.db-wal"
        restored_shm = tmp_path / "restored.db-shm"

        assert restored_wal.exists()
        assert restored_shm.exists()
        assert restored_wal.read_text() == "wal data"
        assert restored_shm.read_text() == "shm data"

    def test_restore_db_backup_nonexistent_backup(self, tmp_path: Path):
        """Test that restoring from nonexistent backup raises error."""
        backup_file = tmp_path / "nonexistent.db"
        db_file = tmp_path / "test.db"

        with pytest.raises(FileNotFoundError, match="Backup file not found"):
            db_backup.restore_db_backup(backup_path=backup_file, db_path=db_file)

    def test_restore_db_backup_creates_target_dir(self, tmp_path: Path):
        """Test that target directory is created if it doesn't exist."""
        backup_file = tmp_path / "backup.db"
        backup_file.write_text("data")

        db_file = tmp_path / "nested" / "db.db"
        assert not db_file.parent.exists()

        db_backup.restore_db_backup(backup_path=backup_file, db_path=db_file)

        assert db_file.exists()

    def test_restore_db_backup_clears_existing_wal_shm(self, tmp_path: Path):
        """Test that existing WAL and SHM files are removed before restore."""
        backup_file = tmp_path / "backup.db"
        backup_file.write_text("data")

        db_file = tmp_path / "test.db"
        db_file.write_text("old data")

        existing_wal = tmp_path / "test.db-wal"
        existing_wal.write_text("old wal")

        existing_shm = tmp_path / "test.db-shm"
        existing_shm.write_text("old shm")

        db_backup.restore_db_backup(backup_path=backup_file, db_path=db_file)

        assert not existing_wal.exists()
        assert not existing_shm.exists()


class TestListBackups:
    """Test cases for list_backups function."""

    def test_list_backups_empty(self, tmp_path: Path):
        """Test listing backups when directory is empty."""
        backups = db_backup.list_backups(tmp_path)

        assert backups == []

    def test_list_backups_nonexistent_dir(self, tmp_path: Path):
        """Test listing backups when directory doesn't exist."""
        backup_dir = tmp_path / "nonexistent"
        backups = db_backup.list_backups(backup_dir)

        assert backups == []

    def test_list_backups_multiple(self, tmp_path: Path):
        """Test listing multiple backups."""
        import os

        base_time = datetime(2025, 12, 30, 12, 0, 0, tzinfo=UTC)

        # Create backups with different timestamps
        for offset in [120, 130, 140]:
            backup = tmp_path / f"wireguard_20251230_{offset:02d}000.db"
            backup.write_text("data")
            # Set modification time to ensure correct ordering
            mtime = (base_time + timedelta(minutes=offset)).timestamp()
            backup.touch()
            os.utime(backup, (mtime, mtime))

        backups = db_backup.list_backups(tmp_path)

        assert len(backups) == 3
        assert backups[0].name == "wireguard_20251230_140000.db"
        assert backups[1].name == "wireguard_20251230_130000.db"
        assert backups[2].name == "wireguard_20251230_120000.db"

    def test_list_backups_excludes_wal_shm(self, tmp_path: Path):
        """Test that WAL and SHM files are not included in list."""
        main_backup = tmp_path / "wireguard_20251230_120000.db"
        main_backup.write_text("data")

        wal_file = tmp_path / "wireguard_20251230_120000.db-wal"
        wal_file.write_text("wal")

        shm_file = tmp_path / "wireguard_20251230_120000.db-shm"
        shm_file.write_text("shm")

        backups = db_backup.list_backups(tmp_path)

        assert len(backups) == 1
        assert backups[0] == main_backup

    def test_list_backups_excludes_wrong_prefix(self, tmp_path: Path):
        """Test that files without correct prefix are not included."""
        valid_backup = tmp_path / "wireguard_20251230_120000.db"
        valid_backup.write_text("valid")

        invalid_file = tmp_path / "other_20251230_120000.db"
        invalid_file.write_text("invalid")

        backups = db_backup.list_backups(tmp_path)

        assert len(backups) == 1
        assert backups[0] == valid_backup


class TestCleanupOldBackups:
    """Test cases for _cleanup_old_backups function."""

    def test_cleanup_old_backups_basic(self, tmp_path: Path, capsys):
        """Test basic cleanup of old backups."""
        import os

        base_time = datetime(2025, 12, 30, 12, 0, 0, tzinfo=UTC)

        for offset in [120, 130, 140, 150, 160]:
            backup = tmp_path / f"wireguard_20251230_{offset:02d}000.db"
            backup.write_text("data")
            # Set modification time to ensure correct ordering
            mtime = (base_time + timedelta(minutes=offset)).timestamp()
            backup.touch()
            os.utime(backup, (mtime, mtime))

        db_backup._cleanup_old_backups(tmp_path, max_backups=3)

        backups = list(tmp_path.glob("*.db"))
        assert len(backups) == 3

        captured = capsys.readouterr()
        assert "Removed old backup:" in captured.out

    def test_cleanup_old_backups_zero(self, tmp_path: Path, capsys):
        """Test that cleanup with max_backups=0 does nothing."""
        backup = tmp_path / "wireguard_20251230_120000.db"
        backup.write_text("data")

        db_backup._cleanup_old_backups(tmp_path, max_backups=0)

        assert backup.exists()
        captured = capsys.readouterr()
        assert "Removed old backup:" not in captured.out

    def test_cleanup_old_backups_negative(self, tmp_path: Path, capsys):
        """Test that cleanup with negative max_backups does nothing."""
        backup = tmp_path / "wireguard_20251230_120000.db"
        backup.write_text("data")

        db_backup._cleanup_old_backups(tmp_path, max_backups=-1)

        assert backup.exists()
        captured = capsys.readouterr()
        assert "Removed old backup:" not in captured.out

    def test_cleanup_old_backups_keep_all(self, tmp_path: Path, capsys):
        """Test that all backups are kept when count <= max_backups."""
        for timestamp in ["120000", "130000", "140000"]:
            backup = tmp_path / f"wireguard_20251230_{timestamp}.db"
            backup.write_text("data")

        db_backup._cleanup_old_backups(tmp_path, max_backups=5)

        backups = list(tmp_path.glob("*.db"))
        assert len(backups) == 3

        captured = capsys.readouterr()
        assert "Removed old backup:" not in captured.out


class TestCopySqliteFiles:
    """Test cases for _copy_sqlite_files helper function."""

    def test_copy_sqlite_files_basic(self, tmp_path: Path):
        """Test copying basic database file."""
        source = tmp_path / "source.db"
        source.write_text("data")

        target = tmp_path / "target.db"

        db_backup._copy_sqlite_files(source, target)

        assert target.exists()
        assert target.read_text() == "data"

    def test_copy_sqlite_files_with_wal_shm(self, tmp_path: Path):
        """Test copying database with WAL and SHM files."""
        source = tmp_path / "source.db"
        source.write_text("db")

        source_wal = tmp_path / "source.db-wal"
        source_wal.write_text("wal")

        source_shm = tmp_path / "source.db-shm"
        source_shm.write_text("shm")

        target = tmp_path / "target.db"

        db_backup._copy_sqlite_files(source, target)

        target_wal = tmp_path / "target.db-wal"
        target_shm = tmp_path / "target.db-shm"

        assert target.read_text() == "db"
        assert target_wal.read_text() == "wal"
        assert target_shm.read_text() == "shm"

    def test_copy_sqlite_files_no_wal_shm(self, tmp_path: Path):
        """Test copying database without WAL and SHM files."""
        source = tmp_path / "source.db"
        source.write_text("data")

        target = tmp_path / "target.db"

        db_backup._copy_sqlite_files(source, target)

        target_wal = tmp_path / "target.db-wal"
        target_shm = tmp_path / "target.db-shm"

        assert target.exists()
        assert not target_wal.exists()
        assert not target_shm.exists()
