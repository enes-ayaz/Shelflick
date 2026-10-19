import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_engine, Base
from app.models import user, media, user_media
from scripts.migrate_watch_time import run_migration

async def init_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables initialized successfully.")
    await run_migration()

if __name__ == "__main__":
    asyncio.run(init_tables())

