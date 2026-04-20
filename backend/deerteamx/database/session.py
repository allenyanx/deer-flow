"""DeerTeamX Database Session Management

Provides async database session factory and dependency injection for FastAPI.
Uses SQLAlchemy 2.0 async engine with connection pooling.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from deerteamx.config.settings import get_settings

# Get settings
settings = get_settings()

# Create async engine with connection pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,  # Number of persistent connections
    max_overflow=20,  # Additional connections beyond pool_size
    pool_timeout=30,  # Seconds to wait for connection from pool
    pool_recycle=1800,  # Recycle connections after 30 minutes
    pool_pre_ping=True,  # Test connections before using
    echo=settings.DEBUG,  # SQL logging in debug mode
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides async database session.
    
    Usage:
        @router.get("/teams")
        async def list_teams(db: AsyncSession = Depends(get_db)):
            ...
    
    Yields:
        AsyncSession instance for database operations
        
    Note:
        Session is automatically closed after request completion.
        Commits must be explicitly called in route handlers.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions (non-FastAPI usage).
    
    Usage:
        async with get_db_context() as db:
            result = await db.execute(select(Team))
    
    Yields:
        AsyncSession instance for database operations
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables (for development/testing only).
    
    WARNING: Do not use in production. Use Alembic migrations instead.
    """
    from deerteamx.models.base import Base
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database engine and all connections."""
    await engine.dispose()
