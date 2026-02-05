#conexión segura a la base de datos
from contextlib import asynccontextmanager
import os

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.pool import NullPool


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@db:5432/pagila"
)

_engine = None
AsyncSessionLocal = None


def get_engine():
    """
    Devuelve un engine async SIN pool (requerido para MCP).
    """
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            poolclass=NullPool,  # 🔑 CLAVE PARA MCP
        )
    return _engine


def get_session_factory():
    """
    Crea (una sola vez) el sessionmaker async.
    """
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        AsyncSessionLocal = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return AsyncSessionLocal


@asynccontextmanager
async def get_db_context():
    """
    Context manager async para usar en las tools MCP.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """
    Inicialización opcional (no crea tablas).
    """
    engine = get_engine()
    async with engine.begin():
        pass


async def close_db():
    """
    Cierre limpio del engine.
    """
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None

