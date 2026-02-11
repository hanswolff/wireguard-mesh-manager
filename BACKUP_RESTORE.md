# Backup and Restore Operations

This document describes how to use the backup and restore functionality of the WireGuard Mesh Manager.

## Overview

The WireGuard Mesh Manager provides two ways to backup and restore your data:

1. **CLI Tool** - Command-line interface for backup/restore operations
2. **API Endpoints** - REST API for programmatic access

Both methods support:

- Full backup of all networks, locations, and devices
- Optional AES encryption with password protection
- Atomic restore operations with conflict detection
- Dry-run mode to preview restore operations

## CLI Tool Usage

### Installation

The CLI tool is automatically installed when you install the package:

```bash
pip install -e backend/
```

The `wmm-backup` command will be available.

### Creating Backups

#### Basic Encrypted Backup

```bash
# Creates an encrypted backup, prompts for password
wmm-backup create -o backup.json

# With description
wmm-backup create -o backup.json -d "Weekly backup"

# With custom exported_by field
wmm-backup create -o backup.json -b "admin@example.com"
```

#### Unencrypted Backup

```bash
# Creates an unencrypted backup (not recommended for production)
wmm-backup create -o backup.json --no-encrypt
```

#### Providing Password Non-interactively

```bash
# Provide password via command line (less secure)
wmm-backup create -o backup.json -p "your-password"

# Use environment variables
export BACKUP_PASSWORD="your-password"
wmm-backup create -o backup.json -p "$BACKUP_PASSWORD"
```

### Viewing Backup Information

```bash
# View backup info (works for encrypted and unencrypted)
wmm-backup info -i backup.json

# Output for encrypted backup:
# 🔒 Backup is encrypted
# 📦 Version: 1.0
# 📊 Use 'restore --dry-run' with password to see contents

# Output for unencrypted backup:
# 📋 Backup Information:
# 📦 Version: 1.0
# 📅 Exported: 2024-01-15T10:30:00+00:00
# 👤 By: admin@example.com
# 📝 Description: Weekly backup
# 📊 Contents:
#   Networks: 2
#   Locations: 4
#   Devices: 12
# 🌐 Networks:
#   • production (10.0.0.0/16) - 8 devices, 2 locations
#   • staging (10.1.0.0/16) - 4 devices, 2 locations
```

### Restoring Backups

#### Dry Run (Recommended First)

```bash
# Preview what would be restored without making changes
wmm-backup restore -i backup.json --dry-run

# Output:
# 🔍 DRY RUN - No changes will be made
# 📅 Export: 2024-01-15T10:30:00+00:00
# 👤 By: admin@example.com
# 📝 Description: Weekly backup
# 📊 Will restore: 2 networks, 4 locations, 12 devices
```

#### Actual Restore

```bash
# Restore from backup (will prompt for password if needed)
wmm-backup restore -i backup.json

# Restore and overwrite existing data
wmm-backup restore -i backup.json --overwrite
```

#### Password Handling

For encrypted backups, you'll be prompted for the password:

```bash
wmm-backup restore -i backup.json
Enter decryption password: ****
```

Or provide it via command line (less secure):

```bash
wmm-backup restore -i backup.json -p "your-password"
```

## API Usage

### Creating Backups

#### Encrypted Backup

```bash
curl -X POST "http://localhost:8000/api/backup/create" \
  -H "Authorization: Master <master-session-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "your-secure-password",
    "description": "API backup",
    "exported_by": "api-user",
    "encrypt": true
  }'
```

#### Unencrypted Backup

```bash
curl -X POST "http://localhost:8000/api/backup/create" \
  -H "Authorization: Master <master-session-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "API backup",
    "exported_by": "api-user",
    "encrypt": false
  }'
```

#### Generate Random Password

```bash
curl -X POST "http://localhost:8000/api/backup/create" \
  -H "Authorization: Master <master-session-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "API backup with random password",
    "exported_by": "api-user",
    "encrypt": true
  }'
```

Response will include the generated password:

```json
{
  "id": "uuid-here",
  "created_at": "2024-01-15T10:30:00Z",
  "description": "API backup with random password",
  "exported_by": "api-user",
  "encrypted": true,
  "networks_count": 2,
  "locations_count": 4,
  "devices_count": 12,
  "password": "generated-random-password",
  "backup_data": {...}
}
```

### Restoring Backups

#### Direct Restore from Backup Data

```bash
curl -X POST "http://localhost:8000/api/backup/restore" \
  -H "Authorization: Master <master-session-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "backup_data": {...},
    "password": "your-password",
    "overwrite_existing": false
  }'
```

#### Upload Backup File

```bash
# Dry run to validate
curl -X POST "http://localhost:8000/api/backup/upload" \
  -H "Authorization: Master <master-session-token>" \
  -F "file=@backup.json" \
  -F "dry_run=true"

# Actual restore
curl -X POST "http://localhost:8000/api/backup/upload" \
  -H "Authorization: Master <master-session-token>" \
  -F "file=@backup.json" \
  -F "password=your-password" \
  -F "overwrite_existing=false"
```

### Getting Backup Information

```bash
curl -X POST "http://localhost:8000/api/backup/info" \
  -H "Authorization: Master <master-session-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "backup_data": {...},
    "password": "your-password"
  }'
```

## Security Considerations

### Encryption

- **Always encrypt backups** when storing or transmitting them
- Use strong passwords (minimum 12 characters, mixed case, numbers, symbols)
- Store passwords securely (password manager, environment variables)
- Never include passwords in logs or commit them to version control

### Password Management

```bash
# Good: Use environment variables
export BACKUP_PASSWORD=$(openssl rand -base64 32)
wmm-backup create -o backup.json -p "$BACKUP_PASSWORD"

# Good: Use password manager
wmm-backup create -o backup.json
# Enter password from password manager when prompted

# Bad: Hardcoded passwords
wmm-backup create -o backup.json -p "password123"
```

### File Permissions

```bash
# Secure backup files
chmod 600 backup.json
chown $USER:$USER backup.json
```

### Audit Trail

All backup and restore operations are automatically logged to the audit events table:

```sql
-- View backup operations
SELECT * FROM audit_events
WHERE action IN ('backup_created', 'backup_restored')
ORDER BY occurred_at DESC;

-- View restore details
SELECT occurred_at, actor, details
FROM audit_events
WHERE action = 'backup_restored';
```

## Best Practices

### Regular Backups

```bash
# Create a cron job for daily backups
0 2 * * * /usr/local/bin/wmm-backup create -o /backups/wmm-$(date +\%Y\%m\%d).json -d "Daily backup" -p "$BACKUP_PASSWORD"
```

### Retention Policy

```bash
# Keep only last 30 days of backups
find /backups -name "wmm-*.json" -mtime +30 -delete
```

### Verification

```bash
# Verify backup integrity
wmm-backup info -i backup.json

# Test restore in staging
wmm-backup restore -i backup.json --dry-run
```

### Disaster Recovery

1. **Store backups off-site** (different geographic location)
2. **Test restores regularly** (monthly drills)
3. **Document the restore process** for your team
4. **Monitor backup success** with alerts

## Troubleshooting

### Common Issues

#### "Password is required for encrypted backup"

The backup is encrypted but no password was provided:

```bash
# Provide password
wmm-backup restore -i backup.json -p "your-password"
```

#### "Failed to decrypt data"

Incorrect password or corrupted backup file:

```bash
# Verify backup info first
wmm-backup info -i backup.json

# Try with correct password
wmm-backup restore -i backup.json -p "correct-password"
```

#### "Network already exists"

Restore conflicts with existing data:

```bash
# Use dry run to see conflicts
wmm-backup restore -i backup.json --dry-run

# Overwrite existing data if desired
wmm-backup restore -i backup.json --overwrite
```

### Getting Help

```bash
# CLI help
wmm-backup --help
wmm-backup create --help
wmm-backup restore --help
wmm-backup info --help

# API documentation
open http://localhost:8000/docs
```

## Integration Examples

### Python Script

```python
import requests
import json
from datetime import datetime

# Create backup
response = requests.post("http://localhost:8000/api/backup/create",
    headers={"Authorization": "Master <master-session-token>"},
    json={
    "description": f"Automated backup {datetime.now()}",
    "exported_by": "automation",
    "encrypt": True
    }
)

backup_data = response.json()

# Save to file with timestamp
filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(filename, 'w') as f:
    json.dump(backup_data['backup_data'], f, indent=2)

print(f"Backup saved to {filename}")
if backup_data.get('password'):
    print(f"Generated password: {backup_data['password']}")
```

### Docker Integration

```dockerfile
# Add backup script to Docker container
COPY backup.sh /usr/local/bin/backup.sh
RUN chmod +x /usr/local/bin/backup.sh

# backup.sh
#!/bin/bash
BACKUP_FILE="/backups/wmm-$(date +%Y%m%d-%H%M%S).json"
wmm-backup create -o "$BACKUP_FILE" -d "Container backup" -p "$BACKUP_PASSWORD"
echo "Backup created: $BACKUP_FILE"
```

## Migration Guide

### From Manual Export

If you were previously using the `/api/export/networks` endpoint directly:

**Old method:**

```bash
curl "http://localhost:8000/api/export/networks?exported_by=admin" \
  -H "Authorization: Master <master-session-token>" > export.json
```

**New method:**

```bash
wmm-backup create -o export.json -b admin -d "Migration backup"
```

### Import Existing Export Files

You can restore files created with the old export endpoint:

```bash
# Old export files work with backup restore
wmm-backup restore -i old-export.json --dry-run
wmm-backup restore -i old-export.json
```
