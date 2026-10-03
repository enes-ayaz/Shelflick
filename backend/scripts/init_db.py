import asyncio
from app.core.database import async_engine, Base
from app.models import user, media, user_media

async def init_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_tables())
