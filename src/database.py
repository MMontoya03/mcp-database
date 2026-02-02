# database.py
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from contextlib import asynccontextmanager
import os
import logging

logger = logging.getLogger(__name__)

# =========================
# DATABASE CONFIG
# =========================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:ecologia@host.docker.internal:5432/pagila"
)


POOL_SIZE = int(os.getenv("POOL_SIZE", 20))
DATABASE_ECHO = os.getenv("DATABASE_ECHO", "False").lower() == "true"

# =========================
# GLOBALS
# =========================

engine = None
AsyncSessionLocal = None


# =========================
# ENGINE
# =========================
def get_engine():
    """Get or create the database engine"""
    global engine
    if engine is None:
        engine = create_async_engine(
            DATABASE_URL,
            echo=DATABASE_ECHO,
            pool_size=POOL_SIZE,
            max_overflow=0,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        logger.info("Database engine created")
    return engine


# =========================
# SESSION FACTORY
# =========================
def get_session_factory():
    """Get or create the async session factory"""
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        AsyncSessionLocal = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
        logger.info("Async session factory created")
    return AsyncSessionLocal


# =========================
# INIT DATABASE
# =========================
async def init_db():
    """
    Initialize database.
    NOTE: Pagila already has tables, so we DO NOT seed data.
    """
    from .models import Base

    logger.info("Initializing database (Pagila)...")

    engine = get_engine()

    async with engine.begin() as conn:
        # Only ensure metadata is loaded (no seed, no fake data)
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized successfully (no seeding)")


# =========================
# DB CONTEXT MANAGER
# =========================
@asynccontextmanager
async def get_db_context():
    """Async context manager for DB sessions"""
    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


# =========================
# CLOSE CONNECTIONS
# =========================
async def close_db():
    """Close database connections"""
    global engine, AsyncSessionLocal

    if engine:
        await engine.dispose()
        engine = None
        AsyncSessionLocal = None
        logger.info("Database connections closed")
