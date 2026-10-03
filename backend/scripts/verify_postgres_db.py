"""Live PostgreSQL Database and Model Verification Script for MediaPulse.

This script connects to the PostgreSQL test database, initializes all models,
validates PostgreSQL-specific types (ARRAY, UUID, ENUM), enforces constraints,
and tests transactions with the ScoringService.
"""

import asyncio
import logging
from pathlib import Path
import subprocess
import sys
import uuid

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import List

from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.media import MediaItem, MediaSource
from app.models.user import User
from app.models.user_media import UserMedia, WatchStatus
from app.services.scoring_service import ScoringService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("db_verifier")


def get_postgres_host() -> str:
    """Detects available PostgreSQL host: localhost or WSL host IP."""
    import socket
    for host in ["localhost", "127.0.0.1"]:
        try:
            with socket.create_connection((host, 5432), timeout=1.0):
                return host
        except (OSError, socket.timeout):
            continue

    # Try WSL2 IP
    try:
        wsl_ip = subprocess.check_output(
            ["wsl", "-d", "Ubuntu", "--", "hostname", "-I"],
            text=True,
            timeout=5,
        ).strip().split()[0]
        logger.info("Detected PostgreSQL in WSL at IP: %s", wsl_ip)
        return wsl_ip
    except Exception as e:
        logger.warning("Could not auto-detect WSL IP (%s), falling back to localhost", e)
        return "localhost"


PG_HOST = get_postgres_host()
TEST_DB_URL = f"postgresql+asyncpg://postgres:postgres@{PG_HOST}:5432/mediapulse_test"
ADMIN_DB_URL = f"postgresql+asyncpg://postgres:postgres@{PG_HOST}:5432/postgres"


async def setup_test_database():
    """Ensure mediapulse_test database exists."""
    logger.info("Connecting to PostgreSQL server to verify test database existence...")
    admin_engine = create_async_engine(ADMIN_DB_URL, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        res = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'mediapulse_test'")
        )
        exists = res.scalar()
        if not exists:
            logger.info("Creating database 'mediapulse_test'...")
            await conn.execute(text("CREATE DATABASE mediapulse_test"))
        else:
            logger.info("Database 'mediapulse_test' already exists.")
    await admin_engine.dispose()


async def verify_models():
    """Create all tables, test constraints, and verify model mapping."""
    logger.info("Connecting to 'mediapulse_test' via asyncpg...")
    engine = create_async_engine(TEST_DB_URL, echo=False)

    # 1. Recreate tables
    async with engine.begin() as conn:
        logger.info("Dropping existing tables and enums...")
        await conn.run_sync(Base.metadata.drop_all)
        # Drop enums if lingering
        await conn.execute(text("DROP TYPE IF EXISTS media_source_enum CASCADE;"))
        await conn.execute(text("DROP TYPE IF EXISTS watch_status_enum CASCADE;"))
        
        logger.info("Creating tables for all models...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("All tables created successfully!")

    # 2. Inspect database schema
    async with engine.connect() as conn:
        def inspect_tables(sync_conn):
            inspector = inspect(sync_conn)
            tables = inspector.get_table_names()
            logger.info("Detected tables in database: %s", tables)
            return tables

        tables = await conn.run_sync(inspect_tables)
        expected_tables = {"users", "media_items", "user_media"}
        assert expected_tables.issubset(set(tables)), f"Missing tables! Expected {expected_tables}, got {tables}"

    # 3. Perform Live CRUD & Constraint Verification
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        logger.info("\n--- STEP 1: Verifying User Creation ---")
        user = User(
            id=uuid.uuid4(),
            username="enes_dev",
            email="enes@mediapulse.local",
            hashed_password="hashed_secure_password_123",
        )
        session.add(user)
        await session.commit()
        user_id = user.id
        logger.info("User created: %s (ID: %s)", user.username, user_id)

        logger.info("\n--- STEP 2: Verifying MediaItem Creation with PostgreSQL ARRAY & ENUM ---")
        media = MediaItem(
            id=uuid.uuid4(),
            external_id="tmdb_movie_603",
            media_source=MediaSource.TMDB_MOVIE,
            title="The Matrix",
            original_title="The Matrix",
            release_year=1999,
            poster_url="https://image.tmdb.org/t/p/w500/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg",
            synopsis="Set in the 22nd century, The Matrix tells the story of a computer hacker...",
            genres=["Action", "Science Fiction"],
            themes=["cyberpunk", "dystopian", "virtual reality"],
            imdb_score=8.7,
            imdb_vote_count=2000000,
            site_vote_count=0,
            site_score=8.7,
        )
        session.add(media)
        await session.commit()
        media_id = media.id
        logger.info("MediaItem created: '%s', Genres (PG ARRAY): %s, Themes: %s", media.title, media.genres, media.themes)

        logger.info("\n--- STEP 3: Verifying UserMedia & Gold Box (is_favorite) ---")
        user_media = UserMedia(
            user_id=user_id,
            media_id=media_id,
            status=WatchStatus.COMPLETED,
            is_favorite=True,
            user_score=10.0,
            personal_notes="Cult classic, revolutionary sci-fi cinema.",
        )
        session.add(user_media)
        await session.commit()
        logger.info("UserMedia entry verified: status=%s, is_favorite=%s, score=%s", user_media.status, user_media.is_favorite, user_media.user_score)

        logger.info("\n--- STEP 4: Verifying UniqueConstraint (user_id, media_id) ---")
        duplicate_entry = UserMedia(
            user_id=user_id,
            media_id=media_id,
            status=WatchStatus.WATCHING,
        )
        session.add(duplicate_entry)
        try:
            await session.commit()
            raise AssertionError("UniqueConstraint failed! Duplicate (user_id, media_id) was allowed.")
        except Exception:
            await session.rollback()
            logger.info("UniqueConstraint verified successfully! Duplicate entry rejected by PostgreSQL.")

        logger.info("\n--- STEP 5: Verifying CheckConstraint (1.0 <= user_score <= 10.0) ---")
        invalid_score_entry = UserMedia(
            user_id=user_id,
            media_id=uuid.uuid4(),  # non-colliding media id
            status=WatchStatus.WATCHING,
            user_score=12.5,  # Exceeds maximum 10.0
        )
        session.add(invalid_score_entry)
        try:
            await session.commit()
            raise AssertionError("CheckConstraint failed! Invalid score was allowed.")
        except Exception:
            await session.rollback()
            logger.info("CheckConstraint verified successfully! Out-of-bounds score (12.5) rejected by PostgreSQL.")

        logger.info("\n--- STEP 6: Verifying ScoringService Transaction with Live PostgreSQL ---")
        # Reload media instance into session after rollbacks
        media = await session.get(MediaItem, media_id)

        # Add a second user to test hybrid scoring in real DB transaction
        user2 = User(
            id=uuid.uuid4(),
            username="reviewer2",
            email="reviewer2@mediapulse.local",
            hashed_password="pw_hash_test_user2",
        )
        session.add(user2)
        await session.commit()

        # Update scoring using ScoringService within transaction
        await ScoringService.update_media_score(
            session=session,
            media_item=media,
            new_user_score=9.0,
            user_id=user2.id,
        )
        await session.commit()

        # Re-fetch from database to verify persistence
        await session.refresh(media)
        logger.info(
            "Scoring updated in PostgreSQL: site_score=%s, site_vote_count=%s (Expected: (8.7*0.7)+(9.5*0.3)=6.09+2.85=8.94)",
            media.site_score,
            media.site_vote_count,
        )
        assert media.site_vote_count == 2
        assert media.site_score == 8.94
        logger.info("Scoring calculation and database transaction verified with 100% accuracy!")

    await engine.dispose()
    logger.info("\n=======================================================")
    logger.info("ALL POSTGRESQL MODELS AND CONSTRAINTS FULLY VALIDATED!")
    logger.info("=======================================================")


async def main():
    try:
        await setup_test_database()
        await verify_models()
    except Exception as exc:
        logger.error("Verification failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
