# Database Migration Backup Strategy

This document describes the backup strategy for database migrations in the WireGuard Mesh Manager.

## Overview

All database migrations automatically create a timestamped backup of the SQLite database file before applying migrations. This ensures that if a migration fails or causes issues, the previous database state can be quickly restored.

## Automatic Backup on Migration

When running `make db-migrate` or `make db-upgrade`, the following happens:

1. A timestamped backup is created: `data/backups/wireguard_YYYYMMDD_HHMMSS.db`
2. All pending Alembic migrations are applied
3. Old backups beyond the configured limit (default: 10) are automatically deleted

## Backup Location

Backups are stored in the `data/backups/` directory with the following naming convention:

```
data/backups/wireguard_YYYYMMDD_HHMMSS.db
```

Example: `data/backups/wireguard_20251230_145453.db`

## SQLite Files Backed Up

For each database backup, the following files are backed up:

1. **Main database file**: `wireguard.db` → `wireguard_YYYYMMDD_HHMMSS.db`
2. **WAL file** (Write-Ahead Log): `wireguard.db-wal` → `wireguard_YYYYMMDD_HHMMSS.db-wal`
3. **SHM file** (Shared Memory): `wireguard.db-shm` → `wireguard_YYYYMMDD_HHMMSS.db-shm`

The WAL and SHM files are SQLite-specific files that contain uncommitted write-ahead log and shared memory data. Backing up these files ensures data consistency.

## Manual Backup Commands

The following Makefile commands are available for manual backup and restore operations:

### Create a Backup

```bash
make db-backup
```

This creates a timestamped backup of the database.

### List All Backups

```bash
make db-list-backups
```

This lists all available backups sorted by modification time (newest first).

Example output:

```
Available backups (newest first):
  wireguard_20251230_145453.db (2025-12-30T19:09:26.884213+00:00) - 102400 bytes
  wireguard_20251230_140000.db (2025-12-30T19:00:00.000000+00:00) - 102400 bytes
```

### Restore from a Backup

```bash
make db-restore BACKUP_FILE=data/backups/wireguard_20251230_145453.db
```

This restores the database from a specific backup file.

### Using the Backup Script Directly

The backup script can also be used directly:

```bash
# Create a backup
python3 scripts/db_backup.py create \
  --db-path data/wireguard.db \
  --backup-dir data/backups \
  --max-backups 10

# Restore from a backup
python3 scripts/db_backup.py restore \
  data/backups/wireguard_20251230_145453.db \
  --db-path data/wireguard.db

# List all backups
python3 scripts/db_backup.py list \
  --backup-dir data/backups
```

## Backup Retention Policy

By default, the backup strategy keeps the 10 most recent database backups. Older backups are automatically deleted when a new backup is created.

The retention limit can be configured by modifying the `max_backups` parameter in the backup command or Makefile.

### Changing the Retention Limit

To change the number of backups to keep, modify the Makefile:

```makefile
db-backup:
	python scripts/db_backup.py create --db-path data/wireguard.db --backup-dir data/backups --max-backups 20
```

Or specify it when creating a backup manually:

```bash
python3 scripts/db_backup.py create --max-backups 20
```

## Recovery from a Failed Migration

If a migration fails, you can restore the database using the most recent backup:

### Option 1: Use the Makefile

```bash
make db-list-backups
# Find the most recent backup
make db-restore BACKUP_FILE=data/backups/wireguard_YYYYMMDD_HHMMSS.db
```

### Option 2: Use the Backup Script

```bash
python3 scripts/db_backup.py restore data/backups/wireguard_YYYYMMDD_HHMMSS.db
```

### Option 3: Manual Restore

```bash
# Stop the application
# Copy the backup file
cp data/backups/wireguard_YYYYMMDD_HHMMSS.db data/wireguard.db

# Also restore WAL and SHM files if they exist
cp data/backups/wireguard_YYYYMMDD_HHMMSS.db-wal data/wireguard.db-wal
cp data/backups/wireguard_YYYYMMDD_HHMMSS.db-shm data/wireguard.db-shm
```

## Troubleshooting

### Backup Creation Fails

If backup creation fails with "Database file not found":

1. Verify that the database path is correct
2. Check that the database file exists at the specified location
3. Ensure proper file permissions

```bash
ls -la data/wireguard.db
```

### Restore Fails

If restore fails:

1. Verify that the backup file exists and is not corrupted
2. Ensure that the application is stopped before restoring
3. Check file permissions on the target database path

```bash
# Check backup file
ls -la data/backups/wireguard_YYYYMMDD_HHMMSS.db

# Check target directory
ls -la data/

# Verify file can be read
file data/backups/wireguard_YYYYMMDD_HHMMSS.db
```

### Multiple Backup Versions

If you see multiple backup files with the same timestamp, it may indicate:

1. The backup script was run multiple times quickly
2. Concurrent backup operations

To resolve:

1. Check which backup file has the correct content and size
2. Remove duplicate backup files manually

```bash
# List backups with sizes
ls -lah data/backups/
```

## Best Practices

### Production Deployment

1. **Regular Backups**: Create backups before running any migration in production
2. **Retention Policy**: Adjust the backup retention limit based on your deployment frequency

3. **Off-site Storage**: For production, consider copying the `data/backups/` directory to off-site storage
4. **Backup Testing**: Periodically test restore operations in a staging environment

### Development

1. **Database Reset**: Use `make db-reset` to reset the database instead of restoring
2. **Quick Iteration**: During development, you can temporarily disable backup creation by modifying the Makefile

### Disaster Recovery

1. **Document the Process**: Ensure your team knows how to restore from backups
2. **Test Recovery Drills**: Regularly practice restoring from backups
3. **Monitor Disk Space**: Ensure adequate disk space for backups in production

## Device DEK migration

The `6c4b1a2f4b91_device_dek_migration` migration re-encrypts device private keys
using per-device DEKs and stores the DEKs encrypted with both the master password
and a device-specific secret.

### Required environment variables

- `WCM_MIGRATION_MASTER_PASSWORD`: The master password used to decrypt existing
  `private_key_encrypted` values.
- `WCM_MIGRATION_DEVICE_API_KEYS`: JSON map of `{ "device_id": "api_key_value" }`.
- `WCM_MIGRATION_DEVICE_MIGRATION_SECRETS`: JSON map of
  `{ "device_id": "temporary_secret" }`.

If a device has no API key available, provide a temporary migration secret for
that device in `WCM_MIGRATION_DEVICE_MIGRATION_SECRETS`. If neither is provided,
the migration fails and you must generate an API key (or supply a temporary
secret) before re-running the migration.

## Security Considerations

### Backup File Permissions

Ensure backup files have appropriate permissions:

```bash
# Set restrictive permissions for production backups
chmod 600 data/backups/wireguard_*.db
```

### Backup Location

For production deployments:

1. Store backups on a different filesystem or drive than the live database
2. Consider using a backup service that provides off-site storage
3. Ensure the backup directory is not served by the web server

### Audit Trail

All database migrations are logged in the audit events table. You can query this to see migration history:

```sql
SELECT occurred_at, actor, details
FROM audit_events
WHERE action IN ('migration_applied', 'migration_rollback')
ORDER BY occurred_at DESC;
```

## Integration with CI/CD

### Automated Testing

In a CI/CD pipeline, you can integrate backup creation before migrations:

```yaml
# Example GitHub Actions workflow
- name: Create database backup before migration
  run: |
    cd backend
    make db-backup

- name: Run database migrations
  run: |
    cd backend
    make db-migrate

- name: Verify migration success
  run: |
    cd backend
    # Verify application starts correctly
    make run &
    sleep 10
    # If application fails, restore from backup
    make db-restore BACKUP_FILE=data/backups/wireguard_$(ls -t data/backups/ | head -1)
```

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [BACKUP_RESTORE.md](./BACKUP_RESTORE.md) - Application-level backup and restore
