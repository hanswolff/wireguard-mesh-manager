# WireGuard Mesh Manager Backend

FastAPI backend service for managing WireGuard VPN networks and devices.

## Development Setup

1. Install Python 3.11+ and create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install development dependencies:

```bash
make install-dev
```

3. Run the development server:

```bash
make run
```

The API will be available at http://localhost:8000

- API Docs: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc

## Local Development Workflow

### First-time Setup

1. Install dependencies and set up pre-commit hooks:

   ```bash
   make install-dev
   ```

2. Initialize the database:

   ```bash
   make db-migrate
   ```

3. Start the development server:
   ```bash
   make run
   ```

### Working with Database Changes

When making database schema changes:

1. After modifying the models, create a new migration:

   ```bash
   make db-revision MSG="describe your change"
   ```

2. Apply the migration:

   ```bash
   make db-migrate
   ```

3. To test a clean migration (useful during development):
   ```bash
   make db-reset
   ```

### Running Tests and Code Quality

Before committing changes:

```bash
make test      # Run tests
make lint      # Check for linting issues
make typecheck # Run type checking
```

The pre-commit hooks will automatically run these checks when you commit.

## Development Commands

- `make install` - Install production dependencies
- `make install-dev` - Install development dependencies and set up pre-commit hooks
- `make test` - Run tests with coverage
- `make lint` - Run ruff linter
- `make format` - Format code with black and ruff
- `make typecheck` - Run mypy type checking
- `make clean` - Clean cache and coverage files
- `make run` - Run the development server with hot reload

### Database Migration Commands

- `make db-migrate` - Apply all pending migrations
- `make db-upgrade` - Upgrade to latest migration (same as db-migrate)
- `make db-downgrade` - Downgrade one migration
- `make db-revision MSG="your message"` - Create a new migration
- `make db-reset` - Reset database and reapply all migrations
- If you are upgrading from a build that used a longer migration chain and Alembic
  cannot find prior revisions, run `alembic stamp head` after verifying the schema
  matches the current release.

## Testing

Run tests with:

```bash
make test
```

Run tests with coverage report:

```bash
pytest --cov=app --cov-report=term-missing
```

## Code Quality

This project uses several tools to maintain code quality:

- **Black**: Code formatting
- **Ruff**: Fast Python linter and formatter
- **MyPy**: Static type checking
- **Pre-commit hooks**: Run quality checks before commits

All these tools are configured in `pyproject.toml` and will run automatically in CI.
