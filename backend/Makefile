.PHONY: help install install-dev test lint format typecheck clean run db-migrate db-upgrade db-downgrade db-revision db-reset db-backup db-restore db-list-backups

help:
	@echo "Available commands:"
	@echo "  install       Install production dependencies"
	@echo "  install-dev   Install development dependencies"
	@echo "  test          Run tests with coverage"
	@echo "  lint          Run ruff linter"
	@echo "  format        Format code with black and ruff"
	@echo "  typecheck     Run mypy type checking"
	@echo "  clean         Clean cache and coverage files"
	@echo "  run           Run the development server"
	@echo ""
	@echo "Database commands:"
	@echo "  db-migrate        Apply all pending migrations (creates backup first)"
	@echo "  db-upgrade        Upgrade to latest migration (same as db-migrate)"
	@echo "  db-downgrade      Downgrade one migration"
	@echo "  db-revision       Create a new migration"
	@echo "  db-reset          Reset database and reapply all migrations"
	@echo ""
	@echo "Database backup commands:"
	@echo "  db-backup         Create a database backup"
	@echo "  db-restore        Restore database from a backup (use: make db-restore BACKUP_FILE=path/to/backup)"
	@echo "  db-list-backups   List all database backups"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt
	pre-commit install

test:
	pytest -v

lint:
	ruff check .

format:
	black .
	ruff format .

typecheck:
	mypy app

clean:
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Database commands
db-migrate:
	python scripts/db_backup.py create --db-path data/wireguard.db --backup-dir data/backups
	alembic upgrade head

db-upgrade:
	python scripts/db_backup.py create --db-path data/wireguard.db --backup-dir data/backups
	alembic upgrade head

db-downgrade:
	alembic downgrade -1

db-revision:
	alembic revision -m "$(MSG)"

db-reset:
	rm -f data/wireguard.db
	alembic upgrade head

# Database backup commands
db-backup:
	python scripts/db_backup.py create --db-path data/wireguard.db --backup-dir data/backups

db-restore:
	python scripts/db_backup.py restore $(BACKUP_FILE) --db-path data/wireguard.db

db-list-backups:
	python scripts/db_backup.py list --backup-dir data/backups
