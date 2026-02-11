# Production Runbook

This runbook covers operational procedures for running the WireGuard Mesh Manager in production, including backup/restore, secret rotation, incident response, and upgrade procedures.

## Table of Contents

1. [Backup and Restore](#backup-and-restore)
2. [Secret Rotation](#secret-rotation)
3. [Incident Response](#incident-response)
4. [Upgrades and Migrations](#upgrades-and-migrations)
5. [Health Checks and Monitoring](#health-checks-and-monitoring)
6. [Emergency Procedures](#emergency-procedures)

## Backup and Restore

### Regular Backup Procedures

#### Database Backups

The SQLite database should be backed up regularly using the built-in backup command:

```bash
# Create a backup (encrypted)
docker-compose exec backend wmm-backup create --output /backups/wireguard-mesh-manager-$(date +%Y%m%d-%H%M%S).json

# Create an unencrypted backup
docker-compose exec backend wmm-backup create --output /backups/wireguard-mesh-manager-$(date +%Y%m%d-%H%M%S).json --no-encrypt
```

**Frequency**: Daily for production environments
**Retention**: Keep 30 days of daily backups, 12 weeks of weekly backups, 12 months of monthly backups

#### Configuration Backups

Back up the complete configuration directory:

```bash
# Backup configuration and environment files
tar -czf /backups/config-$(date +%Y%m%d-%H%M%S).tar.gz \
  /opt/wireguard-mesh-manager/.env \
  /opt/wireguard-mesh-manager/docker-compose.yml \
  /opt/wireguard-mesh-manager/nginx.conf \
  /etc/ssl/wireguard-mesh-manager/ # (if using custom certificates)
```

#### Automated Backup Script

Create a cron job for automated backups:

```bash
# /etc/cron.d/wireguard-mesh-manager-backup
0 2 * * * wireguard-mesh-manager cd /opt/wireguard-mesh-manager && docker-compose exec backend wmm-backup create --output /backups/wireguard-mesh-manager-$(date +\%Y\%m\%d-\%H\%M\%S).json
```

### Restore Procedures

#### Complete System Restore

1. **Prepare the environment**

   ```bash
   # Stop services
   docker-compose down

   # Clear existing data (CAUTION: This is destructive)
   rm -f backend/data/wireguard.db
   ```

2. **Restore database**

   ```bash
   # Restore from backup (will prompt for password if needed)
   docker-compose exec backend wmm-backup restore --input /backups/wireguard-mesh-manager-20240119-020000.json

   # Dry run to see what would be restored
   docker-compose exec backend wmm-backup restore --input /backups/wireguard-mesh-manager-20240119-020000.json --dry-run
   ```

3. **Restore configuration**

   ```bash
   # Restore configuration files
   tar -xzf /backups/config-20240119-020000.tar.gz -C /
   ```

4. **Verify and restart**

   ```bash
   # Start services
   docker-compose up -d

   # Verify health
   curl -f http://localhost:8000/health

   # Verify backup info
   docker-compose exec backend wmm-backup info --input /backups/wireguard-mesh-manager-20240119-020000.json
   ```

#### Automated clean initialization with a new master password

Use the helper script to perform a destructive reset, optionally restore a backup, and rotate the master password in one auditable flow.

```bash
# Destroys backend/data/wireguard.db, restarts containers, restores from the backup, then rotates the master password
# When bootstrapping a fresh database (no backup), you must provide the bootstrap token if BOOTSTRAP_TOKEN is configured
scripts/new-database-with-master-password.sh \
  --new-password "<new-secure-password>" \
  --bootstrap-token "<your-bootstrap-token>" \
  --backup-path /backups/wireguard-mesh-manager-20240119-020000.json
```

**Bootstrap Token Security:**
- Set `BOOTSTRAP_TOKEN` environment variable in your backend config before first deployment
- Generate a secure token: `openssl rand -base64 32`
- This token is required for initial master password unlock when database is empty (fresh install)
- Once the database contains encrypted data (after first network/device creation), the bootstrap token is no longer required
- **If BOOTSTRAP_TOKEN is not configured, the system will accept any non-empty password for initial setup (insecure)**

Notes:
- The script stops containers, deletes `backend/data/wireguard.db`, and exits non-zero on any failure.
- Pass `--api-url` to target a non-default backend endpoint or `--yes` to skip the confirmation prompt (dangerous).
- If `--backup-path` is omitted, a fresh database is created before rotation.
- The rotation runs directly inside the backend container and uses the provided new password as both the current and new value for an empty database.

#### Partial Restore Scenarios

**Restore single network**:

```bash
# Use dry-run to identify the network in the backup
docker-compose exec backend wmm-backup restore --input backup.file --dry-run

# Restore the entire backup and manually manage the specific network
# or use the API to selectively import networks
```

**Recover deleted device**:

```bash
# Check audit logs for device details
grep "device_deleted" /var/log/wireguard-mesh-manager/audit.log | grep <device-name>

# Recreate device with same configuration
# (Use device self-service portal if API key is still valid)
```

### Backup Verification

Regularly test backup integrity:

```bash
# Weekly backup verification
docker-compose exec backend wmm-backup info --input /backups/latest.backup
docker-compose exec backend wmm-backup restore --input /backups/latest.backup --dry-run
```

## Secret Rotation

### Master Password Rotation

The master password protects encrypted private keys at rest.

**Rotation Procedure**:

1. **Ensure system is unlocked**

   ```bash
   # Check current master password status
   curl -X GET http://localhost:8000/api/master-password/status \
     -H "Authorization: Master <master-session-token>"
   ```

2. **Initiate rotation**

   ```bash
   # Start rotation process
   curl -X POST http://localhost:8000/api/key-rotation/rotate \
  -H "Authorization: Master <master-session-token>" \
     -H "Content-Type: application/json" \
     -d '{"current_password": "<current-password>", "new_password": "<new-secure-password>", "confirm_password": "<new-secure-password>"}'
   ```

3. **Verify rotation**
   ```bash
   # Test unlock with new password
   # Note: bootstrap_token is not required when database has encrypted data
   curl -X POST http://localhost:8000/api/master-password/unlock \
     -H "Content-Type: application/json" \
     -d '{"master_password": "<new-secure-password>"}'
   ```

**Frequency**: Quarterly or immediately if password compromise is suspected

### Database Encryption Key Rotation

Note: Database encryption key rotation should be handled through the application's master password rotation feature, which automatically re-encrypts the database with new keys. See the Master Password Rotation section above.

### API Key Rotation

#### Device API Keys

For individual devices:

```bash
# Get existing API keys for device
curl -X GET http://localhost:8000/api/api-keys/device/<device-id> \
  -H "Authorization: Master <master-session-token>"

# Rotate existing API key
curl -X POST http://localhost:8000/api/api-keys/<api-key-id>/rotate \
  -H "Authorization: Master <master-session-token>"

# Create new API key if none exists
curl -X POST http://localhost:8000/api/api-keys \
  -H "Authorization: Master <master-session-token>" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "<device-id>", "name": "Device API Key", "allowed_ip_ranges": "0.0.0.0/0"}'

# Update device configuration with new key
# (Device will need to fetch new config)
```

#### Admin Sessions

Admin access is gated by the master password and a master session token. To
obtain a new token, unlock the master password:

```bash
# For initial setup on fresh database (no encrypted data yet):
curl -X POST http://localhost:8000/master-password/unlock \
  -H "Content-Type: application/json" \
  -d '{"master_password": "<master-password>", "bootstrap_token": "<your-bootstrap-token>"}'

# After initial setup (database has encrypted data), bootstrap_token is not required:
curl -X POST http://localhost:8000/master-password/unlock \
  -H "Content-Type: application/json" \
  -d '{"master_password": "<master-password>"}'
```

### Certificate Rotation

If using custom TLS certificates:

```bash
# Generate new certificates
openssl req -x509 -newkey rsa:4096 -keyout new.key -out new.crt -days 365 -nodes

# Update configuration
# (Edit nginx.conf or docker-compose.yml with new certificate paths)

# Reload nginx
docker-compose exec nginx nginx -s reload
```

## Incident Response

### Security Incident Categories

#### 1. Unauthorized Access

**Symptoms**:

- Unexpected audit log entries
- Failed authentication attempts
- Device configuration access from unknown IPs

**Response**:

```bash
# Revoke a specific device (disables device and all its API keys)
curl -X POST http://localhost:8000/api/devices/<device-id>/revoke \
  -H "Authorization: Master <master-session-token>"

# Revoke all API keys for a specific device
curl -X POST http://localhost:8000/api/api-keys/<api-key-id>/revoke \
  -H "Authorization: Master <master-session-token>"

# List all API keys for a device
curl -X GET http://localhost:8000/api/api-keys/device/<device-id> \
  -H "Authorization: Master <master-session-token>"

# Rotate master password
# (See Master Password Rotation section)

# Re-unlock master password as needed
```

#### 2. Data Corruption

**Symptoms**:

- Database integrity errors
- Inconsistent network configurations
- Application crashes

**Response**:

1. **Immediate isolation**

   ```bash
   # Stop services to prevent further corruption
   docker-compose down

   # Backup current (potentially corrupted) state
   cp backend/data/wireguard.db backend/data/wireguard.db.corrupted.$(date +%s)
   ```

2. **Assessment**

   ```bash
   # Check database integrity
   sqlite3 backend/data/wireguard.db "PRAGMA integrity_check;"

   # Review recent audit logs for suspicious activity
   tail -n 1000 /var/log/wireguard-mesh-manager/audit.log
   ```

3. **Recovery**

   ```bash
   # Restore from most recent known-good backup
   docker-compose exec backend wmm-backup restore --input /backups/wireguard-mesh-manager-last-known-good.backup

   # Verify integrity after restore
   curl -f http://localhost:8000/health
   ```

#### 3. Service Outage

**Symptoms**:

- Health check failures
- Connection timeouts
- High error rates

**Response**:

1. **Diagnose**

   ```bash
   # Check service status
   docker-compose ps

   # Review logs
   docker-compose logs --tail=100 backend
   docker-compose logs --tail=100 frontend

   # Check system resources
   df -h
   free -h
   ```

2. **Restart services**

   ```bash
   # Clean restart
   docker-compose down
   docker-compose up -d

   # Verify health
   curl -f http://localhost:8000/health
   ```

3. **If restart fails**:

   ```bash
   # Check for port conflicts
   netstat -tulpn | grep :8000

   # Check disk space
   df -h

   # Check memory usage
   free -h
   ```

### Incident Communication

**Internal Notification Process**:

1. Page on-call engineer immediately (Severity 1)
2. Create incident ticket with details
3. Update status every 30 minutes during active incident
4. Post-mortem within 24 hours of resolution

**External Communication** (if applicable):

1. Prepare customer impact assessment
2. Draft status page updates
3. Coordinate with communications team
4. Send post-incident summary

### Post-Incident Procedures

1. **Root Cause Analysis**

   ```bash
   # Preserve logs for analysis
   tar -czf incident-$(date +%Y%m%d).tar.gz \
     /var/log/wireguard-mesh-manager/ \
     docker-compose logs
   ```

2. **Documentation Updates**

   - Update runbook with new procedures
   - Add monitoring for detected issues
   - Improve alerting thresholds

3. **Prevention Measures**
   - Implement automated monitoring
   - Add additional health checks
   - Improve backup frequency if needed

## Upgrades and Migrations

### Pre-Upgrade Checklist

- [ ] Verify current system health
- [ ] Create full backup
- [ ] Review upgrade notes for target version
- [ ] Schedule maintenance window (if required)
- [ ] Prepare rollback plan
- [ ] Test upgrade in staging environment

### Upgrade Procedure

#### Minor Version Upgrades (Patch releases)

```bash
# Pull latest images
docker-compose pull

# Restart with new images
docker-compose up -d

# Verify health
curl -f http://localhost:8000/health
curl -f http://localhost:3000
```

#### Major Version Upgrades

1. **Prepare**

   ```bash
   # Stop services
   docker-compose down

   # Backup current configuration
   cp docker-compose.yml docker-compose.yml.backup
   cp .env .env.backup
   ```

2. **Update configuration**

   ```bash
   # Get new configuration files from your internal release artifact/source control
   # (example paths shown; adjust to your environment)
   cp /path/to/release/docker-compose.yml .
   cp /path/to/release/.env.example .

   # Merge custom configurations
   # (Compare backup files with new versions)
   ```

3. **Database migrations**

   ```bash
   # Start backend only for migrations
   docker-compose up -d backend

   # Migrations are automatically applied on startup
   # Check application logs to verify migration success
   docker-compose logs backend
   ```

   If you are upgrading from a release that used a longer migration chain and
   Alembic reports missing revisions, verify the schema matches the current
   release and then stamp the database:

   ```bash
   docker-compose exec backend alembic stamp head
   ```

4. **Complete upgrade**

   ```bash
   # Start all services
   docker-compose up -d

   # Verify functionality
   curl -f http://localhost:8000/health
   curl -f http://localhost:3000
   ```

### Rollback Procedure

If upgrade fails:

1. **Quick rollback** (within 15 minutes)

   ```bash
   # Stop services
   docker-compose down

   # Restore configuration
   cp docker-compose.yml.backup docker-compose.yml
   cp .env.backup .env

   # Restart with previous version
   docker-compose up -d

   # Verify health
   curl -f http://localhost:8000/health
   ```

2. **Full rollback** (including database)

   ```bash
   # Stop services
   docker-compose down

   # Restore database from pre-upgrade backup
   docker-compose exec backend wmm-backup restore --input /backups/pre-upgrade.backup

   # Restore configuration
   cp docker-compose.yml.backup docker-compose.yml
   cp .env.backup .env

   # Restart services
   docker-compose up -d
   ```

### Data Migration Procedures

#### Host Migration

1. **Prepare new host**

   ```bash
   # Install dependencies
   apt-get update && apt-get install -y docker docker-compose

   # Create directories
   mkdir -p /opt/wireguard-mesh-manager/{data,backups,logs}
   ```

2. **Transfer data**

   ```bash
   # On old host: create migration bundle
   tar -czf /tmp/wireguard-mesh-manager-migration.tar.gz \
     /opt/wireguard-mesh-manager/data/ \
     /opt/wireguard-mesh-manager/.env \
     /opt/wireguard-mesh-manager/docker-compose.yml

   # Transfer to new host
   scp /tmp/wireguard-mesh-manager-migration.tar.gz user@new-host:/tmp/
   ```

3. **Restore on new host**

   ```bash
   # Extract migration bundle
   tar -xzf /tmp/wireguard-mesh-manager-migration.tar.gz -C /

   # Start services
   cd /opt/wireguard-mesh-manager
   docker-compose up -d

   # Update DNS/firewall to point to new host
   ```

## Health Checks and Monitoring

### Automated Health Checks

```bash
# Application health
curl -f http://localhost:8000/health

# Database connectivity
curl -f http://localhost:8000/health/db

# Frontend availability
curl -f http://localhost:3000

# API functionality
curl -f http://localhost:8000/api/networks \
  -H "Authorization: Master <test-token>"
```

### Monitoring Metrics

Key metrics to monitor:

- **Application metrics**

  - Request response times
  - Error rates (4xx, 5xx)
  - Authentication success/failure rates
  - Database query performance

- **System metrics**

  - CPU utilization
  - Memory usage
  - Disk space
  - Network I/O

- **Business metrics**
  - Number of active networks
  - Device registration rates
  - Config download frequency

### Alerting Thresholds

Recommended alert thresholds:

- **Critical**: Service down > 1 minute
- **Warning**: Response time > 2 seconds
- **Warning**: Error rate > 1%
- **Critical**: Disk space < 10%
- **Warning**: Memory usage > 80%

## Emergency Procedures

### Complete System Lockdown

In case of security emergency:

```bash
# Revoke all devices in a network (disables them)
# Repeat for each network or write a script to do it for all
curl -X POST http://localhost:8000/api/devices/<device-id>/revoke \
  -H "Authorization: Master <master-session-token>"

# Alternative: Stop services
docker-compose down

# Block network access (if needed)
iptables -A INPUT -p tcp --dport 8000 -j DROP
iptables -A INPUT -p tcp --dport 3000 -j DROP
```

### Data Wiping (Decommissioning)

For secure decommissioning:

```bash
# Stop services
docker-compose down

# Securely delete database
shred -vfz -n 3 backend/data/wireguard.db

# Securely delete backups
find /backups/ -type f -exec shred -vfz -n 3 {} \;

# Delete configuration files containing secrets
shred -vfz -n 3 .env
shred -vfz -n 3 docker-compose.yml

# Clear logs
shred -vfz -n 3 /var/log/wireguard-mesh-manager/*
```

### Recovery from Total Loss

If all data is lost:

1. **Assess what can be recovered**

   - Check for recent backups
   - Review configuration exports
   - Contact stakeholders for manual network/device information

2. **Rebuild from scratch**

   ```bash
   # Start with fresh installation
   git clone https://github.com/hanswolff/wireguard-mesh-manager
   cd wireguard-mesh-manager

   # Configure new instance
   cp .env.example .env
   # Edit .env with appropriate settings

   # Start services
   docker-compose up -d
   ```

3. **Manual data entry**
   - Recreate networks based on documentation
   - Register devices manually
   - Generate new WireGuard keys
   - Update all device configurations

## Contacts and Escalation

- **On-call Engineer**: [Phone number]
- **Engineering Manager**: [Phone number]
- **Security Team**: [Phone number]
- **Infrastructure Team**: [Phone number]

## Related Documentation

- [Threat Model](THREAT_MODEL.md)
- [Deployment Topology](DEPLOYMENT_TOPOLOGY.md)
- [API Versioning Policy](api-versioning-policy.md)
- [Docker Security](docker-security.md)

---

Last updated: 2025-12-19
Version: 1.0
