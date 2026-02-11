# Coding Conventions

This document defines the coding conventions for the WireGuard Mesh Manager project to ensure consistency, readability, and maintainability across the entire codebase.

## Table of Contents

1. [General Principles](#general-principles)
2. [Python (Backend)](#python-backend)
3. [TypeScript/JavaScript (Frontend)](#typescriptjavascript-frontend)
4. [Documentation](#documentation)
5. [Error Handling](#error-handling)
6. [Logging](#logging)
7. [Security](#security)
8. [Tool Configuration](#tool-configuration)

## General Principles

- **Clarity over cleverness**: Write code that is easy to understand
- **Consistency**: Follow established patterns in the codebase
- **Security first**: Never expose sensitive information
- **Type safety**: Use strong typing wherever possible
- **Testability**: Write code that is easy to test

## Python (Backend)

### Code Style

We use **Black** for code formatting with these settings:

- Line length: 88 characters
- Target Python version: 3.11+
- Use double quotes for strings

```python
# Good
def process_network_data(
    network_id: str,
    include_devices: bool = False,
) -> dict[str, Any]:
    """Process network data and return structured results."""
    return {"network_id": network_id, "devices": []}
```

### Import Organization

Use **isort** (via ruff) for import organization:

1. Standard library imports
2. Third-party imports
3. Local application imports
4. Relative imports

```python
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from sqlalchemy import select

from app.database.models import Network, Device
from app.exceptions import ResourceNotFoundError
from app.schemas.networks import NetworkCreate
```

### Type Hints

- Use strict type hints for all function parameters and return values
- Use `from __future__ import annotations` to avoid circular imports
- Prefer built-in generic types (Python 3.9+): `dict[str, int]` over `Dict[str, int]`

```python
# Good
async def create_network(
    db: AsyncSession,
    network_data: NetworkCreate,
) -> Network:
    """Create a new network."""
    pass

# Bad
async def create_network(db, network_data):
    """Create a new network."""
    pass
```

### Naming Conventions

- **Variables and functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private members**: Leading underscore `_private_method`

```python
MAX_RETRY_ATTEMPTS = 3

class NetworkService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _validate_network(self, network_id: str) -> bool:
        """Private method for validation."""
        return True

    async def create_network(self, network_data: NetworkCreate) -> Network:
        """Create a new network."""
        pass
```

### Error Handling

- Use custom exception classes from `app.exceptions`
- Always include descriptive error messages
- Use structured logging for errors (see Logging section)

```python
# Good
if not network:
    raise ResourceNotFoundError("Network", network_id)

# Bad
if not network:
    raise HTTPException(404, "Network not found")
```

### Async/Await

- Use `async/await` consistently for I/O operations
- Always specify return types for async functions

```python
# Good
async def get_devices(self, network_id: str) -> list[Device]:
    result = await self.db.execute(select(Device).where(Device.network_id == network_id))
    return list(result.scalars().all())
```

## TypeScript/JavaScript (Frontend)

### Code Style

We use **Prettier** for consistent formatting:

- Semi-colons: required
- Quotes: single quotes
- Trailing commas: ES5
- Tab width: 2 spaces
- Arrow parentheses: always

```typescript
// Good
const fetchNetworkData = async (
  networkId: string,
  includeDevices = false
): Promise<NetworkData> => {
  try {
    const response = await apiClient.get(`/networks/${networkId}`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch network data:', error);
    throw error;
  }
};
```

### Import Organization

```typescript
// React imports first
import { useState, useEffect } from 'react';
import Link from 'next/link';

// Third-party libraries
import { Button } from '@/components/ui/button';
import { Activity, Shield } from 'lucide-react';

// Local imports
import { apiClient } from '@/lib/api';
import { NetworkData } from '@/types';
```

### Type Definitions

- Use TypeScript interfaces/type aliases for all data structures
- Prefer explicit return types for functions
- Use generic types where appropriate

```typescript
// Good
interface Network {
  id: string;
  name: string;
  cidr: string;
  locations: Location[];
  createdAt: Date;
}

interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}

const fetchNetworks = async (): Promise<Network[]> => {
  const response = await apiClient.get<ApiResponse<Network[]>>('/networks');
  return response.data.data;
};
```

### Component Patterns

- Use functional components with hooks
- Define props interfaces explicitly
- Use proper TypeScript for event handlers

```typescript
// Good
interface NetworkCardProps {
  network: Network;
  onEdit: (network: Network) => void;
  onDelete: (networkId: string) => void;
}

export const NetworkCard: React.FC<NetworkCardProps> = ({
  network,
  onEdit,
  onDelete,
}) => {
  const handleDelete = () => {
    onDelete(network.id);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{network.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <Button onClick={() => onEdit(network)}>Edit</Button>
        <Button variant="destructive" onClick={handleDelete}>
          Delete
        </Button>
      </CardContent>
    </Card>
  );
};
```

### Naming Conventions

- **Components**: `PascalCase`
- **Variables and functions**: `camelCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Interfaces and types**: `PascalCase`
- **Files**: `kebab-case` for components, `camelCase` for utilities

## Documentation

### Docstrings (Python)

Use Google-style docstrings:

```python
def create_network(self, network_data: NetworkCreate) -> Network:
    """Create a new WireGuard network.

    Args:
        network_data: The network data to create.

    Returns:
        The created network instance.

    Raises:
        ResourceConflictError: If a network with the same name already exists.
    """
    pass
```

### JSDoc (TypeScript)

```typescript
/**
 * Fetches network data from the API.
 *
 * @param networkId - The ID of the network to fetch
 * @param includeDevices - Whether to include device data
 * @returns Promise resolving to network data
 * @throws {ApiError} When the network is not found
 */
const fetchNetwork = async (
  networkId: string,
  includeDevices = false
): Promise<Network> => {
  // Implementation
};
```

### Comments

- Write comments that explain **why**, not **what**
- Use TODO/FIXME comments for temporary solutions
- Keep comments up-to-date with code changes

```python
# Good: Explains why we're doing something
# Use a transaction to ensure atomicity when creating network and default location
async def create_network_with_location(self, network_data: NetworkCreate) -> Network:
    async with self.db.begin():
        network = Network(**network_data.model_dump())
        self.db.add(network)

        # Create default location for the network
        default_location = Location(
            network_id=network.id,
            name="Default",
            description="Default location for the network"
        )
        self.db.add(default_location)

        # Transaction commits automatically
        return network
```

## Error Handling

### Backend (Python)

- Use custom exception classes from `app.exceptions`
- Include context-specific error messages
- Log errors with appropriate context (never log sensitive data)

```python
from app.exceptions import ResourceNotFoundError, BusinessRuleViolationError
from app.utils.logging import get_logger

logger = get_logger(__name__)

async def delete_network(self, network_id: str) -> None:
    """Delete a network."""
    network = await self.get_network(network_id)

    # Check for associated devices
    device_count = await self.db.execute(
        select(Device).where(Device.network_id == network_id)
    )
    if device_count.scalars():
        logger.warning(
            "Attempted to delete network with associated devices",
            extra={
                "network_id": network_id,
                "device_count": len(list(device_count.scalars())),
            },
        )
        raise BusinessRuleViolationError(
            "network_with_devices",
            "Cannot delete network that has devices. Delete all devices first.",
        )

    await self.db.delete(network)
    await self.db.commit()

    logger.info(
        "Network deleted successfully",
        extra={"network_id": network_id},
    )
```

### Frontend (TypeScript)

- Use try-catch blocks for async operations
- Provide user-friendly error messages
- Log errors appropriately (never expose sensitive data)

```typescript
const handleDeleteNetwork = async (networkId: string) => {
  try {
    setLoading(true);
    setError(null);

    await apiClient.delete(`/networks/${networkId}`);

    // Refresh the network list
    await fetchNetworks();

    toast({
      title: 'Success',
      description: 'Network deleted successfully',
    });
  } catch (error) {
    console.error('Failed to delete network:', error);
    setError('Unable to delete network. Please try again.');

    toast({
      title: 'Error',
      description: 'Failed to delete network. Please try again.',
      variant: 'destructive',
    });
  } finally {
    setLoading(false);
  }
};
```

## Logging

### Backend (Python)

Use the structured logging utility from `app.utils.logging`:

```python
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Include context in structured logs
logger.info(
    "Processing network request",
    extra={
        "network_id": network.id,
        "user_id": user.id,
        "request_id": request_id,
        "action": "create_network",
    },
)

# Never log sensitive data
logger.info(
    "API key created",
    extra={
        "device_id": device.id,
        "key_length": len(api_key),  # Log length, not the key itself
    },
)
```

### Redaction Rules

**Never log:**

- API keys, passwords, or secrets
- Private keys or encryption keys
- User passwords or master passwords
- IP addresses in production (unless specifically needed for security)

**Always redact:**

- Replace sensitive values with `[REDACTED]`
- Use hash values for comparison when needed

```python
# Good - redacted logging
logger.info(
    "Device authenticated",
    extra={
        "device_id": device.id,
        "api_key_hash": hash_api_key(api_key),  # Hash for identification
        "source_ip": request.client.host,  # OK for security monitoring
    },
)

# Bad - exposing secrets
logger.info(
    "Device authenticated",
    extra={
        "device_id": device.id,
        "api_key": api_key,  # NEVER log raw API keys
        "private_key": private_key,  # NEVER log private keys
    },
)
```

## Security

### Input Validation

- Always validate user input at API boundaries
- Use Pydantic schemas for request validation
- Sanitize data before database operations

### Secret Management

- Never hardcode secrets in code
- Use environment variables for configuration
- Implement proper secret rotation procedures

### Output Encoding

- Escape user-generated content in UI
- Use parameterized queries to prevent SQL injection
- Validate and serialize API responses

## Tool Configuration

### Backend (Python)

The project uses these tools for enforcing conventions:

1. **Black**: Code formatting
2. **Ruff**: Linting and import sorting
3. **MyPy**: Type checking
4. **Pre-commit**: Git hooks for automated checks

Configuration files:

- `backend/pyproject.toml`: Tool configurations
- `backend/.pre-commit-config.yaml`: Pre-commit hooks

### Frontend (TypeScript)

The project uses these tools for enforcing conventions:

1. **ESLint**: Linting and code quality
2. **Prettier**: Code formatting
3. **TypeScript**: Type checking

Configuration files:

- `frontend/eslint.config.mjs`: ESLint configuration
- `frontend/.prettierrc`: Prettier configuration
- `frontend/tsconfig.json`: TypeScript configuration

### Pre-commit Hooks

The project enforces coding conventions through pre-commit hooks:

```bash
# Install pre-commit hooks
pip install pre-commit
cd backend && pre-commit install

# Run pre-commit hooks manually
pre-commit run --all-files
```

### CI/CD Integration

All code changes must pass:

- Type checking (MyPy/TypeScript)
- Linting (Ruff/ESLint)
- Formatting (Black/Prettier)
- Tests (pytest/Playwright)

## Review Guidelines

When reviewing code changes, check for:

1. **Adherence to conventions**: Is the code consistent with this guide?
2. **Type safety**: Are all types properly specified?
3. **Error handling**: Are errors handled appropriately?
4. **Security**: Are there any security vulnerabilities?
5. **Documentation**: Is the code well-documented?
6. **Tests**: Does the code have adequate test coverage?

## Examples

### Complete Backend Example

```python
"""Service for managing WireGuard network operations."""

from __future__ import annotations

from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Network, Device
from app.exceptions import ResourceNotFoundError, BusinessRuleViolationError
from app.schemas.networks import NetworkCreate, NetworkUpdate
from app.utils.logging import get_logger

logger = get_logger(__name__)

MAX_NETWORK_NAME_LENGTH = 255

class NetworkService:
    """Service for managing WireGuard networks."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service with database session."""
        self.db = db

    async def list_networks(self) -> List[Network]:
        """Get all networks with their device counts."""
        result = await self.db.execute(
            select(Network).options(selectinload(Network.devices))
        )
        networks = list(result.scalars().all())

        logger.info(
            "Retrieved network list",
            extra={"network_count": len(networks)},
        )

        return networks

    async def create_network(self, network_data: NetworkCreate) -> Network:
        """Create a new network.

        Args:
            network_data: The network data to create.

        Returns:
            The created network instance.

        Raises:
            ResourceConflictError: If network name already exists.
        """
        # Validate name length
        if len(network_data.name) > MAX_NETWORK_NAME_LENGTH:
            raise ValueError(f"Network name too long (max {MAX_NETWORK_NAME_LENGTH} chars)")

        # Check for existing network with same name
        existing = await self.db.execute(
            select(Network).where(Network.name == network_data.name)
        )
        if existing.scalar_one_or_none():
            raise ResourceConflictError(
                f"Network with name '{network_data.name}' already exists"
            )

        network = Network(**network_data.model_dump())
        self.db.add(network)
        await self.db.commit()
        await self.db.refresh(network)

        logger.info(
            "Network created successfully",
            extra={
                "network_id": network.id,
                "network_name": network.name,
                "cidr": network.cidr,
            },
        )

        return network
```

### Complete Frontend Example

```typescript
/** Component for displaying and managing network cards. */

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Network, Device } from '@/types';
import { apiClient } from '@/lib/api';
import { toast } from '@/components/ui/use-toast';

interface NetworkCardProps {
  network: Network;
  onUpdate: (network: Network) => void;
  onDelete: (networkId: string) => void;
}

/** Displays network information and provides management actions. */
export const NetworkCard: React.FC<NetworkCardProps> = ({
  network,
  onUpdate,
  onDelete,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this network?')) {
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      await apiClient.delete(`/networks/${network.id}`);
      onDelete(network.id);

      toast({
        title: 'Success',
        description: 'Network deleted successfully',
      });
    } catch (err) {
      console.error('Failed to delete network:', err);
      setError('Failed to delete network');

      toast({
        title: 'Error',
        description: 'Unable to delete network. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{network.name}</CardTitle>
          <Badge variant={network.is_active ? 'default' : 'secondary'}>
            {network.is_active ? 'Active' : 'Inactive'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="font-medium">CIDR:</span>
            <p className="text-muted-foreground">{network.cidr}</p>
          </div>
          <div>
            <span className="font-medium">Devices:</span>
            <p className="text-muted-foreground">{network.devices.length}</p>
          </div>
        </div>

        {error && (
          <div className="text-sm text-destructive">
            {error}
          </div>
        )}

        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onUpdate(network)}
            disabled={isLoading}
          >
            Edit
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={handleDelete}
            disabled={isLoading}
          >
            {isLoading ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
```

---

**Remember**: The goal of these conventions is to create maintainable, secure, and readable code. When in doubt, prioritize clarity and consistency.
