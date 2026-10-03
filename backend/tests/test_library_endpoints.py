import uuid
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.media import MediaItem, MediaSource
from app.models.user import User
from app.models.user_media import UserMedia, WatchStatus


@pytest.mark.asyncio
async def test_add_to_library_and_get_items():
    """Verify POST /api/v1/library/items creates a media item and links it to the user."""
    mock_session = AsyncMock(spec=AsyncSession)

    # 1. Mock demo user lookup
    demo_user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        username="demo_user",
        email="demo@shelflick.local",
        hashed_password="pw",
    )

    # 2. Mock MediaItem & UserMedia
    test_media_id = uuid.uuid4()
    db_media = MediaItem(
        id=test_media_id,
        external_id="16498",
        media_source=MediaSource.ANILIST,
        title="Monster",
        release_year=2004,
        poster_url="https://image.url/monster.jpg",
        synopsis="A brilliant doctor faces a dark monster.",
        genres=["Psychological", "Thriller"],
        themes=["serial killer"],
        site_score=8.8,
    )

    user_media = UserMedia(
        id=uuid.uuid4(),
        user_id=demo_user.id,
        media_id=test_media_id,
        status=WatchStatus.PLAN_TO_WATCH,
        is_favorite=False,
    )

    # Return None for initial finds, then user/media
    sync_result_user = MagicMock()
    sync_result_user.scalars.return_value.first.return_value = demo_user

    sync_result_none = MagicMock()
    sync_result_none.scalars.return_value.first.return_value = None

    # For GET items: return list of tuples (user_media, db_media)
    sync_result_get = MagicMock()
    sync_result_get.all.return_value = [(user_media, db_media)]

    mock_session.execute.side_effect = [
        sync_result_user,   # get_or_create_demo_user
        sync_result_none,   # check existing MediaItem (returns None, triggers add)
        sync_result_none,   # check existing UserMedia (returns None, triggers add)
        sync_result_get,    # get_library_items
    ]

    async def _mock_db():
        yield mock_session

    app.dependency_overrides[get_db] = _mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test POST /api/v1/library/items
        payload = {
            "media": {
                "external_id": "16498",
                "source": "ANILIST",
                "title": "Monster",
                "release_year": 2004,
                "poster_url": "https://image.url/monster.jpg",
                "synopsis": "A brilliant doctor faces a dark monster.",
                "genres": ["Psychological", "Thriller"],
                "themes": ["serial killer"],
                "base_score": 8.8,
                "vote_count": 140000,
            },
            "status": "PLAN_TO_WATCH",
            "is_favorite": False,
        }
        res_post = await client.post("/api/v1/library/items", json=payload)
        assert res_post.status_code == 201
        data = res_post.json()
        assert data["title"] == "Monster"
        assert data["external_id"] == "16498"
        assert data["status"] == "PLAN_TO_WATCH"

        # Test GET /api/v1/library/items
        res_get = await client.get("/api/v1/library/items")
        assert res_get.status_code == 200
        items = res_get.json()
        assert len(items) == 1
        assert items[0]["title"] == "Monster"

    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_random_recommendation_filters_saved_library_titles():
    """Verify get_random_masterpiece excludes media that the user already has in UserMedia."""
    from app.services.llm.recommendation_engine import RecommendationEngine
    from app.schemas.unified_media import UnifiedMediaDTO

    mock_llm = AsyncMock()
    mock_llm.generate_json.return_value = {
        "candidate_index": 0,
        "two_sentence_justification": "Zamansız bir şaheser. Kesinlikle izlemelisin.",
        "confidence_score": 0.98,
        "matched_attributes": ["başyapıt"],
    }

    engine = RecommendationEngine(llm_client=mock_llm)

    # Mock user session having "Monster" in their library
    mock_session = AsyncMock(spec=AsyncSession)
    user_id = uuid.uuid4()

    mock_exec_result_user = MagicMock()
    mock_exec_result_user.all.return_value = [("Monster", "16498")]

    mock_exec_result_db = MagicMock()
    mock_exec_result_db.scalars.return_value.first.return_value = None

    mock_session.execute.side_effect = [mock_exec_result_user, mock_exec_result_db]


    # Provide candidate items: Monster and Vinland Saga
    candidate1 = UnifiedMediaDTO(
        external_id="16498",
        source="ANILIST",
        title="Monster",
        poster_url="https://url/monster.jpg",
        synopsis="Synopsis",
        genres=["Drama"],
        themes=["mystery"],
        base_score=8.8,
        vote_count=1000,
    )
    candidate2 = UnifiedMediaDTO(
        external_id="101348",
        source="ANILIST",
        title="Vinland Saga",
        poster_url="https://url/vinland.jpg",
        synopsis="Viking saga",
        genres=["Action"],
        themes=["history"],
        base_score=8.9,
        vote_count=2000,
    )

    with patch(
        "app.services.media_aggregator.MediaAggregatorService.get_random_masterpieces",
        new=AsyncMock(return_value=[candidate1, candidate2]),
    ):


        result = await engine.get_random_masterpiece(user_id=user_id, session=mock_session)
        # Monster is filtered out because user already saved it!
        assert result.recommended_media is not None
        assert result.recommended_media.title != "Monster"
        assert result.recommended_media.title == "Vinland Saga"
