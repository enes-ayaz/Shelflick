import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def migrate():
    async with AsyncSessionLocal() as session:
        print("Migrating users table...")
        await session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255) DEFAULT '';"))
        await session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255) UNIQUE;"))
        await session.execute(text("ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL;"))
        await session.execute(text("ALTER TABLE users ALTER COLUMN username DROP NOT NULL;"))
        # Also populate existing users with a default name if blank
        await session.execute(text("UPDATE users SET name = username WHERE name = '' OR name IS NULL;"))
        await session.commit()
        print("Migration applied successfully!")

        res = await session.execute(text("SELECT column_name, is_nullable FROM information_schema.columns WHERE table_name = 'users';"))
        for col, nullable in res.fetchall():
            print(f"  {col}: nullable={nullable}")

if __name__ == "__main__":
    asyncio.run(migrate())
