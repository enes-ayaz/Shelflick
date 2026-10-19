import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.media import MediaItem, MediaSource
from app.models.user import User
from app.models.user_media import UserMedia, WatchStatus
from app.schemas.unified_media import UnifiedMediaDTO
from app.services.external.anilist_client import AniListClient
from app.services.external.tmdb_client import TMDBClient


@pytest.mark.asyncio
async def test_completed_status_auto_sync_episodes():
    """Verify that when a media is added with COMPLETED status and no watched_episodes,

    watched_episodes is automatically set to total_episodes.
    """
    mock_session = AsyncMock(spec=AsyncSession)

    demo_user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        username="demo_user",
        email="demo@shelflick.local",
    )

    sync_user = MagicMock()
    sync_user.scalars.return_value.first.return_value = demo_user

    sync_none = MagicMock()
    sync_none.scalars.return_value.first.return_value = None

    mock_session.execute.side_effect = [
        sync_user,  # get_or_create_demo_user
        sync_none,  # find MediaItem (None -> creates new)
        sync_none,  # find UserMedia (None -> creates new)
    ]

    async def _mock_db():
        yield mock_session

    app.dependency_overrides[get_db] = _mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "media": {
                "external_id": "99999",
                "source": "TMDB_SERIES",
                "title": "Breaking Code",
                "release_year": 2022,
                "poster_url": "https://image.url/poster.jpg",
                "synopsis": "A programmer cooks good code.",
                "genres": ["Drama"],
                "themes": ["programming"],
                "base_score": 9.2,
                "vote_count": 5000,
                "runtime": 50,
                "total_episodes": 62,
                "total_seasons": 5,
                "airing_status": "Ended",
            },
            "status": "COMPLETED",
            # watched_episodes intentionally omitted
        }
        res = await client.post("/api/v1/library/items", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["watched_episodes"] == 62
        assert data["watched_seasons"] == 5
        assert data["runtime"] == 50
        assert data["airing_status"] == "Ended"

    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_watching_status_explicit_episodes():
    """Verify that when a user provides watched_episodes with WATCHING status,

    that exact number is preserved.
    """
    mock_session = AsyncMock(spec=AsyncSession)

    demo_user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        username="demo_user",
        email="demo@shelflick.local",
    )

    sync_user = MagicMock()
    sync_user.scalars.return_value.first.return_value = demo_user

    sync_none = MagicMock()
    sync_none.scalars.return_value.first.return_value = None

    mock_session.execute.side_effect = [
        sync_user,
        sync_none,
        sync_none,
    ]

    async def _mock_db():
        yield mock_session

    app.dependency_overrides[get_db] = _mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "media": {
                "external_id": "88888",
                "source": "ANILIST",
                "title": "Steins;Gate",
                "release_year": 2011,
                "poster_url": "https://image.url/steins.jpg",
                "synopsis": "Time travel thriller.",
                "genres": ["Sci-Fi"],
                "themes": ["time travel"],
                "base_score": 9.1,
                "vote_count": 80000,
                "runtime": 24,
                "total_episodes": 24,
                "airing_status": "FINISHED",
            },
            "status": "WATCHING",
            "watched_episodes": 14,
            "watched_seasons": 1,
        }
        res = await client.post("/api/v1/library/items", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["watched_episodes"] == 14
        assert data["watched_seasons"] == 1

    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_library_stats_calculation_and_season_radar():
    """Verify GET /api/v1/library/stats calculations and season radar filtering."""
    mock_session = AsyncMock(spec=AsyncSession)

    demo_user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        username="demo_user",
    )

    # Item 1: Movie with runtime=150, COMPLETED (1 ep watched)
    m1 = MediaItem(
        id=uuid.uuid4(),
        external_id="101",
        media_source=MediaSource.TMDB_MOVIE,
        title="Interstellar",
        poster_url="https://image.url/interstellar.jpg",
        synopsis="Space exploration.",
        runtime=150,
        total_episodes=1,
        airing_status="Released",
    )
    um1 = UserMedia(
        id=uuid.uuid4(),
        user_id=demo_user.id,
        media_id=m1.id,
        status=WatchStatus.COMPLETED,
        watched_episodes=1,
        watched_seasons=1,
    )

    # Item 2: Series with runtime=None (fallback 45 min), WATCHING (10 eps watched), Returning Series
    m2 = MediaItem(
        id=uuid.uuid4(),
        external_id="102",
        media_source=MediaSource.TMDB_SERIES,
        title="House of the Dragon",
        poster_url="https://image.url/hotd.jpg",
        synopsis="Targaryen civil war.",
        runtime=None,  # Should fallback to 45 min
        total_episodes=20,
        total_seasons=2,
        airing_status="Returning Series",
        next_airing_info={"air_date": "2026-06-15", "episode_number": 1, "season_number": 3},
    )
    um2 = UserMedia(
        id=uuid.uuid4(),
        user_id=demo_user.id,
        media_id=m2.id,
        status=WatchStatus.WATCHING,
        watched_episodes=10,
        watched_seasons=1,
    )

    # Item 3: Anime with runtime=None (fallback 24 min), PLAN_TO_WATCH (0 eps watched), RELEASING
    m3 = MediaItem(
        id=uuid.uuid4(),
        external_id="103",
        media_source=MediaSource.ANILIST,
        title="Jujutsu Kaisen Season 3",
        poster_url="https://image.url/jjk.jpg",
        synopsis="Cursed energy battles.",
        runtime=None,  # Should fallback to 24 min
        total_episodes=24,
        airing_status="RELEASING",
        next_airing_info={"airingAt": 1750000000, "episode": 5},
    )
    um3 = UserMedia(
        id=uuid.uuid4(),
        user_id=demo_user.id,
        media_id=m3.id,
        status=WatchStatus.PLAN_TO_WATCH,
        watched_episodes=0,
        watched_seasons=0,
    )

    sync_stats = MagicMock()
    sync_stats.all.return_value = [
        (um1, m1),
        (um2, m2),
        (um3, m3),
    ]

    mock_session.execute.return_value = sync_stats

    async def _mock_db():
        yield mock_session

    app.dependency_overrides[get_db] = _mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/library/stats")
        assert res.status_code == 200
        data = res.json()

        # Calculation check:
        # m1: 1 episode * 150 min = 150 min
        # m2: 10 episodes * 45 min (default) = 450 min
        # m3: 0 episodes * 24 min = 0 min
        # Total minutes = 150 + 450 = 600 min (10 hours, 0 days, 0 min)
        # Total episodes = 1 + 10 + 0 = 11
        assert data["total_watch_time_minutes"] == 600
        assert data["total_episodes_watched"] == 11
        assert data["total_watch_time_formatted"]["days"] == 0
        assert data["total_watch_time_formatted"]["hours"] == 10
        assert data["total_watch_time_formatted"]["minutes"] == 0

        # Radar items check:
        # m1: "Released", no next airing -> NOT in radar
        # m2: "Returning Series" + next_airing_info, WATCHING -> IN radar
        # m3: "RELEASING" + next_airing_info, PLAN_TO_WATCH -> IN radar
        radar = data["radar_items"]
        assert len(radar) == 2
        radar_titles = [item["title"] for item in radar]
        assert "House of the Dragon" in radar_titles
        assert "Jujutsu Kaisen Season 3" in radar_titles
        assert "Interstellar" not in radar_titles

    app.dependency_overrides.pop(get_db, None)


def test_anilist_dto_mapping_watch_time():
    """Verify AniList client parses duration, episodes, status, nextAiringEpisode."""
    client = AniListClient()
    raw = {
        "id": 1535,
        "title": {"english": "Death Note", "romaji": "Death Note"},
        "description": "A notebook of death.",
        "startDate": {"year": 2006},
        "coverImage": {"large": "https://image.url/cover.jpg"},
        "genres": ["Mystery", "Supernatural"],
        "tags": [{"name": "psychological", "rank": 90, "isMediaSpoiler": False}],
        "averageScore": 84,
        "popularity": 350000,
        "duration": 23,
        "episodes": 37,
        "status": "FINISHED",
        "nextAiringEpisode": None,
    }
    dto = client._item_to_dto(raw)
    assert dto is not None
    assert dto.runtime == 23
    assert dto.total_episodes == 37
    assert dto.airing_status == "FINISHED"
    assert dto.next_airing_info is None


def test_tmdb_dto_mapping_watch_time_series():
    """Verify TMDB client parses TV details including episode_run_time, status, next_episode_to_air."""
    client = TMDBClient()
    raw_tv = {
        "id": 1399,
        "media_type": "tv",
        "name": "Game of Thrones",
        "original_name": "Game of Thrones",
        "first_air_date": "2011-04-17",
        "poster_path": "/u3bZgnGQ9T01sWNhyveQz0wH0Hl.jpg",
        "overview": "Seven noble families fight for control.",
        "genres": [{"id": 10765, "name": "Sci-Fi & Fantasy"}],
        "vote_average": 8.4,
        "vote_count": 22000,
        "episode_run_time": [55, 60, 50],
        "number_of_episodes": 73,
        "number_of_seasons": 8,
        "status": "Ended",
        "next_episode_to_air": None,
    }
    dto = client._item_to_dto(raw_tv)
    assert dto is not None
    assert dto.runtime == 55  # Average of [55, 60, 50] = 55
    assert dto.total_episodes == 73
    assert dto.total_seasons == 8
    assert dto.airing_status == "Ended"
    assert dto.next_airing_info is None
