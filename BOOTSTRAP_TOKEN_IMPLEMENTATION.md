# Bootstrap Token Implementation

## Overview

This document describes the implementation of bootstrap token authorization for initial master-password unlock, which prevents unauthenticated takeover on fresh installs.

## Problem Statement

Previously, the master-password unlock endpoint (`POST /api/master-password/unlock`) accepted any non-empty password when the database was empty (fresh install with no encrypted data). This created a critical security vulnerability where anyone could call the unlock endpoint with any password and gain admin access.

## Solution

Implemented an explicit bootstrap token requirement for initial master-password unlock when the database is empty. Once bootstrapped (database contains encrypted data), the bootstrap token is no longer required.

## Implementation Details

### 1. Configuration Setting

**File**: `backend/app/config.py`

Added a new configuration setting:

```python
bootstrap_token: str = ""  # Token required for initial unlock when DB is empty
```

- **Default**: Empty string (insecure, but backward compatible)
- **Production**: Should be set to a secure random value (e.g., `openssl rand -base64 32`)
- **Security Impact**: If empty, the system accepts any password for initial setup (insecure)

### 2. API Request Model

**File**: `backend/app/routers/master_password.py`

Added an optional field to `MasterPasswordUnlockRequest`:

```python
bootstrap_token: str | None = Field(
    None,
    description=(
        "Bootstrap token required for initial unlock when database is empty. "
        "Not required once bootstrapped (has encrypted data)."
    ),
)
```

### 3. Unlock Endpoint Logic

**File**: `backend/app/routers/master_password.py`

Modified the `unlock_master_password()` function to:

1. Check if the database has encrypted data (network or device with encrypted keys)
2. If the database is empty (bootstrap scenario):
   - If `bootstrap_token` is configured in settings:
     - Require a valid bootstrap token in the request
     - Use `secrets.compare_digest()` for timing-resistant comparison
     - Return 403 Forbidden if missing or invalid
   - If `bootstrap_token` is not configured:
     - Accept any non-empty password (backward compatible)
     - Log a warning about insecure configuration
3. If the database has encrypted data (already bootstrapped):
   - Ignore the bootstrap token (not needed)
   - Validate only the master password against encrypted data

### 4. Security Features

- **Timing-resistant comparison**: Uses `secrets.compare_digest()` for constant-time comparison
- **One-time use**: Bootstrap token is only required for initial setup, not subsequent unlocks
- **Audit logging**: All bootstrap attempts are logged with security-relevant metadata
- **Backward compatibility**: If bootstrap_token is not configured, the system behaves as before (with warning)

### 5. Script Updates

**File**: `scripts/new-database-with-master-password.sh`

- Added `--bootstrap-token` command-line option
- Modified the unlock payload to include the bootstrap token if provided
- Updated documentation and usage message

### 6. Documentation Updates

**Files Updated**:
- `README.md`: Added bootstrap token configuration in deployment section
- `PRODUCTION_RUNBOOK.md`: Added bootstrap token security requirements
- `docker-compose.yml` and `docker-compose.prod.yml`: Added bootstrap token configuration comments
- `docker-compose.prod.yml`: Added bootstrap token configuration comments

### 7. Tests

**File**: `backend/tests/test_bootstrap_auth.py`

Comprehensive test coverage for:

1. **Empty DB without bootstrap token** → Should fail with 403
2. **Empty DB with valid bootstrap token** → Should succeed with 200
3. **Empty DB with invalid bootstrap token** → Should fail with 403
4. **Empty DB without bootstrap token configured** → Should succeed (insecure mode)
5. **Bootstrapped DB (has data)** → Bootstrap token ignored, only password validated
6. **Bootstrapped DB with wrong password** → Should fail with 401
7. **Empty password validation** → Should fail with 422
8. **Timing-resistant comparison** → Uses `secrets.compare_digest()`

## Deployment Guide

### For Fresh Installations

1. **Generate a secure bootstrap token**:
   ```bash
   openssl rand -base64 32
   ```

2. **Configure the bootstrap token in the environment**:
   ```bash
   # docker-compose.yml
   environment:
     - BOOTSTRAP_TOKEN=your-secure-token-here

   # docker-compose.prod.yml
   environment:
     - BOOTSTRAP_TOKEN=your-secure-token-here
   ```

3. **Unlock the master password for initial setup**:
   ```bash
   # Include the bootstrap token in the initial unlock request
   curl -X POST http://localhost:8000/api/master-password/unlock \
     -H "Content-Type: application/json" \
     -d '{
       "master_password": "your-secure-password",
       "bootstrap_token": "your-secure-token-here"
     }'
   ```

4. **After initial setup (first network/device created)**:
   - The bootstrap token is no longer required
   - Only the master password is validated

### For Using the Helper Script

```bash
scripts/new-database-with-master-password.sh \
  --new-password "your-secure-password" \
  --bootstrap-token "your-secure-token-here"
```

## Security Considerations

### Threat Model

**Before fix**:
- Anyone who can reach the unlock endpoint can call it with any password on a fresh install
- No out-of-band authorization for initial setup
- An attacker can immediately gain admin access

**After fix**:
- Only someone who knows the bootstrap token can perform the initial setup
- The bootstrap token is an out-of-band secret (not transmitted via the application itself)
- An attacker must have access to the deployment environment or infrastructure

### Best Practices

1. **Generate secure tokens**: Use cryptographically secure random token generation
2. **Never commit tokens**: The bootstrap token should be in environment variables, not in code
3. **Rotate tokens**: If the bootstrap token is compromised, change it immediately
4. **Log attempts**: All bootstrap attempts are logged for audit trails
5. **Use secure channels**: Distribute the bootstrap token via secure means (not email, chat)

### Backward Compatibility

The implementation maintains backward compatibility:

- If `BOOTSTRAP_TOKEN` is not configured (empty string), the system behaves as before
- Logs a warning when accepting any password in this mode
- Once bootstrapped, the bootstrap token setting becomes irrelevant

### Migration Guide

For existing installations:

1. **If already bootstrapped** (has networks/devices):
   - No action is required
   - The bootstrap token is not used
   - The system works as before

2. **If fresh install** (no encrypted data):
   - Set the `BOOTSTRAP_TOKEN` environment variable
   - Use the bootstrap token in the initial unlock request
   - After the first network/device is created, the bootstrap token is no longer needed

## Testing

Run the bootstrap authorization tests:

```bash
cd backend
pytest tests/test_bootstrap_auth.py -v
```

**Note**: Tests require proper database isolation. The `db_session` fixture creates a fresh in-memory database for each test to ensure test isolation.

## Summary

This implementation addresses a critical security vulnerability by requiring explicit out-of-band authorization (a bootstrap token) for initial system setup. The token is only required once (when the database is empty), and normal password-based authentication takes over after the system is bootstrapped with encrypted data.

The implementation maintains backward compatibility by allowing the system to operate without a bootstrap token (with security warnings) while strongly recommending that all production deployments configure and use a secure bootstrap token.
