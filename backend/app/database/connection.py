"""Database connection configuration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Import all models to ensure they're registered
from app.database.models import Base  # noqa: F401, E402

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# Create async engine for SQLite using settings
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session with proper error handling (FastAPI dependency)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except SQLAlchemyError:
            await session.rollback()
            raise
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session with proper error handling."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except SQLAlchemyError:
            await session.rollback()
            raise
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize the database by creating all tables."""
    try:
        # Ensure data directory exists
        db_path = Path(settings.database_url.replace("sqlite+aiosqlite:///", ""))
        data_dir = db_path.parent
        data_dir.mkdir(exist_ok=True, parents=True)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except SQLAlchemyError as e:
        raise RuntimeError(f"Failed to initialize database: {e}") from e
