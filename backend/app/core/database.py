from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all SQLAlchemy 2.0 declarative models."""
    pass


import logging
import re
import socket
import subprocess

logger = logging.getLogger(__name__)


def resolve_postgres_url(original_url: str) -> str:
    """Verifies that the PostgreSQL host in the URL is reachable; falls back to WSL IP if needed in local dev."""
    # In cloud / production environment, strictly honor the configured DATABASE_URL directly from .env
    if settings.ENVIRONMENT in ("production", "staging"):
        return original_url

    # Check if host in original URL is reachable
    match = re.search(r"@([^:/]+):(\d+)", original_url)
    if match:
        configured_host = match.group(1)
        port = int(match.group(2))
        try:
            with socket.create_connection((configured_host, port), timeout=1.0):
                return original_url
        except Exception:
            pass

    # Try known WSL IP
    for host in ["172.26.7.84", "127.0.0.1", "localhost"]:
        try:
            with socket.create_connection((host, 5432), timeout=1.0):
                return re.sub(r"@[^:/]+:\d+", f"@{host}:5432", original_url)
        except Exception:
            pass

    # Dynamic WSL IP query
    try:
        wsl_ip = subprocess.check_output(
            ["wsl", "-d", "Ubuntu", "--", "hostname", "-I"],
            text=True,
            timeout=4,
        ).strip().split()[0]
        with socket.create_connection((wsl_ip, 5432), timeout=1.0):
            return re.sub(r"@[^:/]+:\d+", f"@{wsl_ip}:5432", original_url)
    except Exception:
        pass

    return original_url


EFFECTIVE_DATABASE_URL = resolve_postgres_url(settings.DATABASE_URL)

# Asynchronous SQLAlchemy Engine
async_engine: AsyncEngine = create_async_engine(
    url=EFFECTIVE_DATABASE_URL,
    echo=settings.DEBUG or settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True,
    future=True,
)

# Asynchronous Session Factory
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for yielding an asynchronous database session.

    Ensures proper rollback on unhandled exceptions and cleans up session on exit.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
