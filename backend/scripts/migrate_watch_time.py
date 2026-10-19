import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal, async_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_migration():
    """Migrates database schema to include watch time and new season radar fields."""
    logger.info("Starting watch time and season radar database migration...")

    async with AsyncSessionLocal() as session:
        dialect_name = session.bind.dialect.name if session.bind else "postgresql"
        logger.info("Detected database dialect: %s", dialect_name)

        if dialect_name == "postgresql":
            # PostgreSQL schema updates
            logger.info("Applying PostgreSQL column migrations...")
            await session.execute(text("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS runtime INTEGER;"))
            await session.execute(text("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS total_episodes INTEGER DEFAULT 1;"))
            await session.execute(text("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS total_seasons INTEGER;"))
            await session.execute(text("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS airing_status VARCHAR(100);"))
            await session.execute(text("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS next_airing_info JSON;"))

            await session.execute(text("ALTER TABLE user_media ADD COLUMN IF NOT EXISTS watched_episodes INTEGER DEFAULT 0;"))
            await session.execute(text("ALTER TABLE user_media ADD COLUMN IF NOT EXISTS watched_seasons INTEGER DEFAULT 0;"))

            # Backfill existing COMPLETED entries where watched_episodes is 0
            logger.info("Backfilling watched_episodes for existing COMPLETED records...")
            await session.execute(text("""
                UPDATE user_media
                SET watched_episodes = COALESCE(media_items.total_episodes, 1)
                FROM media_items
                WHERE user_media.media_id = media_items.id
                  AND user_media.status = 'COMPLETED'
                  AND (user_media.watched_episodes IS NULL OR user_media.watched_episodes = 0);
            """))

            await session.commit()
            logger.info("PostgreSQL migration applied successfully!")

        else:
            # Generic / SQLite schema updates
            logger.info("Applying generic column migrations for %s...", dialect_name)
            columns_to_add = [
                ("media_items", "runtime", "INTEGER"),
                ("media_items", "total_episodes", "INTEGER DEFAULT 1"),
                ("media_items", "total_seasons", "INTEGER"),
                ("media_items", "airing_status", "VARCHAR(100)"),
                ("media_items", "next_airing_info", "JSON"),
                ("user_media", "watched_episodes", "INTEGER DEFAULT 0"),
                ("user_media", "watched_seasons", "INTEGER DEFAULT 0"),
            ]
            for table, col, col_type in columns_to_add:
                try:
                    await session.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};"))
                    await session.commit()
                    logger.info("Added %s.%s successfully.", table, col)
                except Exception as e:
                    # Column might already exist
                    logger.debug("Column %s.%s could not be added (might exist): %s", table, col, e)
                    await session.rollback()

            # Backfill completed items
            try:
                await session.execute(text("""
                    UPDATE user_media
                    SET watched_episodes = (
                        SELECT COALESCE(media_items.total_episodes, 1)
                        FROM media_items
                        WHERE media_items.id = user_media.media_id
                    )
                    WHERE user_media.status = 'COMPLETED'
                      AND (user_media.watched_episodes IS NULL OR user_media.watched_episodes = 0);
                """))
                await session.commit()
            except Exception as e:
                logger.warning("Backfill query failed: %s", e)
                await session.rollback()

    logger.info("Watch time & season radar migration finished successfully.")


if __name__ == "__main__":
    asyncio.run(run_migration())
