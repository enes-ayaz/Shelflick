from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import async_engine

logger = logging.getLogger(__name__)


from sqlalchemy import text

POSTGRES_MIGRATIONS = [
    # media_items columns
    "ALTER TABLE media_items ADD COLUMN IF NOT EXISTS original_title VARCHAR(255);",
    "ALTER TABLE media_items ADD COLUMN IF NOT EXISTS release_year INTEGER;",
    "ALTER TABLE media_items ADD COLUMN IF NOT EXISTS poster_url VARCHAR(1024) DEFAULT '';",
    "ALTER TABLE media_items ADD COLUMN IF NOT EXISTS synopsis TEXT DEFAULT '';",
    "ALTER TABLE media_items ADD COLUMN IF NOT EXISTS genres VARCHAR[] DEFAULT '{}';",
    "ALTER TABLE media_items ADD COLUMN IF NOT EXISTS themes VARCHAR[] DEFAULT '{}';",
    "ALTER TABLE media_items ADD COLUMN IF NOT EXISTS imdb_score FLOAT;",
    "ALTER TABLE media_items ADD COLUMN IF NOT EXISTS imdb_vote_count INTEGER DEFAULT 0;",
    "ALTER TABLE media_items ADD COLUMN IF NOT EXISTS site_score FLOAT;",
    "ALTER TABLE media_items ADD COLUMN IF NOT EXISTS site_vote_count INTEGER DEFAULT 0;",
    "ALTER TABLE media_items ADD COLUMN IF NOT EXISTS runtime INTEGER;",
    "ALTER TABLE media_items ADD COLUMN IF NOT EXISTS total_episodes INTEGER DEFAULT 1;",
    "ALTER TABLE media_items ADD COLUMN IF NOT EXISTS total_seasons INTEGER;",
    "ALTER TABLE media_items ADD COLUMN IF NOT EXISTS airing_status VARCHAR(100);",
    "ALTER TABLE media_items ADD COLUMN IF NOT EXISTS next_airing_info JSON;",

    # user_media columns
    "ALTER TABLE user_media ADD COLUMN IF NOT EXISTS is_favorite BOOLEAN DEFAULT FALSE;",
    "ALTER TABLE user_media ADD COLUMN IF NOT EXISTS user_score FLOAT;",
    "ALTER TABLE user_media ADD COLUMN IF NOT EXISTS drop_reason VARCHAR(255);",
    "ALTER TABLE user_media ADD COLUMN IF NOT EXISTS personal_notes TEXT;",
    "ALTER TABLE user_media ADD COLUMN IF NOT EXISTS watched_episodes INTEGER DEFAULT 0;",
    "ALTER TABLE user_media ADD COLUMN IF NOT EXISTS watched_seasons INTEGER DEFAULT 0;",
    "ALTER TABLE user_media ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();",
    "ALTER TABLE user_media ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();",

    # users columns
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255) DEFAULT '';",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(50);",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255);",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255);",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255);",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();",

    # Ensure demo user exists
    """
    INSERT INTO users (id, name, username, email, hashed_password)
    VALUES ('00000000-0000-0000-0000-000000000001', 'Demo User', 'demo_user', 'demo@shelflick.local', 'mock_password_hash')
    ON CONFLICT (id) DO NOTHING;
    """,
]


async def apply_migrations(conn) -> list[str]:
    applied: list[str] = []
    if conn.dialect.name == "postgresql":
        for stmt in POSTGRES_MIGRATIONS:
            try:
                await conn.execute(text(stmt))
                applied.append(stmt.strip().split("\n")[0])
            except Exception as exc:
                logger.warning("Migration statement skipped: %s -> %s", stmt.strip()[:50], exc)
    return applied


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifespan handler."""
    logger.info("Starting up %s (env=%s)...", settings.PROJECT_NAME, settings.ENVIRONMENT)
    try:
        from app.core.database import Base, async_engine
        import app.models  # noqa: F401
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await apply_migrations(conn)
        logger.info("Database schema verified, migrated, and ready.")
    except Exception as e:
        logger.warning("Could not auto-verify database schema on startup: %s", e)
    yield
    logger.info("Shutting down %s, closing database engine...", settings.PROJECT_NAME)
    await async_engine.dispose()


def create_application() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Cross-Origin Resource Sharing (CORS)
    cors_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://shelflick.com",
        "https://www.shelflick.com",
    ]
    frontend_url = os.getenv("FRONTEND_URL")
    if frontend_url and frontend_url not in cors_origins:
        cors_origins.append(frontend_url.rstrip("/"))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|([a-zA-Z0-9-]+\.)*vercel\.app|([a-zA-Z0-9-]+\.)*shelflick\.com)(:[0-9]+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Root and Health check
    @app.get("/", tags=["System"])
    async def root():
        return {
            "message": "Shelflick API is running",
            "docs": "/docs",
            "health": "/health",
            "version": settings.PROJECT_VERSION,
        }

    @app.get("/health", tags=["System"])
    async def health_check():
        db_status = "unknown"
        try:
            async with async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"

        return {
            "status": "healthy" if db_status == "connected" else "degraded",
            "database": db_status,
            "project": settings.PROJECT_NAME,
            "version": settings.PROJECT_VERSION,
        }

    @app.post("/api/v1/system/migrate", tags=["System"])
    async def run_system_migration():
        try:
            from app.core.database import Base
            import app.models  # noqa: F401
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                applied = await apply_migrations(conn)
            return {"status": "ok", "applied_count": len(applied), "applied": applied}
        except Exception as e:
            logger.exception("Manual migration failed: %s", e)
            return {"status": "error", "detail": str(e)}

    # Mount API v1 router
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_application()
