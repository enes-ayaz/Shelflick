import pytest
import pytest_asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.media import MediaItem, MediaSource
from app.models.user import User
from app.models.user_media import UserMedia, WatchStatus
from app.services.scoring_service import ScoringService


@pytest_asyncio.fixture
async def async_db_session():
    """Provides an isolated in-memory SQLite async session for testing transactions."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_update_media_score_transaction_with_users(async_db_session: AsyncSession):
    """Test full async database transaction workflow with users rating media."""
    # 1. Create MediaItem
    media = MediaItem(
        id=uuid.uuid4(),
        external_id="tmdb_test_99",
        media_source=MediaSource.TMDB_MOVIE,
        title="Interstellar",
        poster_url="https://image.tmdb.org/poster.jpg",
        synopsis="A team of explorers travel through a wormhole in space...",
        imdb_score=8.6,
        site_vote_count=0,
        site_score=8.6,
    )
    # 2. Create User 1
    user1 = User(
        id=uuid.uuid4(),
        username="cooper",
        email="cooper@endurance.space",
        hashed_password="hashed_pw_secret",
    )
    # 3. Create User 2
    user2 = User(
        id=uuid.uuid4(),
        username="brand",
        email="brand@endurance.space",
        hashed_password="hashed_pw_secret",
    )

    async_db_session.add_all([media, user1, user2])
    await async_db_session.commit()

    # User 1 rates 10.0
    await ScoringService.update_media_score(
        session=async_db_session,
        media_item=media,
        new_user_score=10.0,
        user_id=user1.id,
    )
    await async_db_session.commit()

    # Vote count = 1 -> Rule 2: (8.6 * 0.70) + (10.0 * 0.30) = 6.02 + 3.00 = 9.02
    assert media.site_vote_count == 1
    assert media.site_score == 9.02

    # User 2 rates 8.0
    await ScoringService.update_media_score(
        session=async_db_session,
        media_item=media,
        new_user_score=8.0,
        user_id=user2.id,
    )
    await async_db_session.commit()

    # Avg of (10.0 + 8.0) / 2 = 9.0
    # Vote count = 2 -> Rule 2: (8.6 * 0.70) + (9.0 * 0.30) = 6.02 + 2.70 = 8.72
    assert media.site_vote_count == 2
    assert media.site_score == 8.72
