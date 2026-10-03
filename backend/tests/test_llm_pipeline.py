import pytest
import pytest_asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.schemas.unified_media import UnifiedMediaDTO
from app.services.llm.recommendation_engine import LLMClient, RecommendationEngine
from app.services.llm.schemas import (
    RecommendationResult,
    UserIntentFilter,
    UserLibraryProfile,
)


@pytest_asyncio.fixture(autouse=True)
async def override_db_dependency():
    """Provides a safe isolated DB session for FastAPI endpoint tests."""
    mock_session = AsyncMock(spec=AsyncSession)
    sync_result = MagicMock()
    sync_result.scalars.return_value.first.return_value = None
    sync_result.scalars.return_value.all.return_value = []
    sync_result.all.return_value = []
    mock_session.execute.return_value = sync_result

    async def _mock_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _mock_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_intent_parsing_stage_a():
    """Verify Stage A extracts structured intent filters from natural language."""
    mock_llm = AsyncMock(spec=LLMClient)
    mock_llm.generate_json.return_value = {
        "is_direct_title_search": False,
        "direct_title": None,
        "media_type_filter": "ANIME",
        "mood_keywords": ["karanlık", "gerilim", "tekinsiz"],
        "target_themes": ["psikolojik", "distopya"],
        "excluded_tropes": ["shounen klişesi", "arkadaşlık gücü"],
        "reference_titles": [],
    }

    engine = RecommendationEngine(llm_client=mock_llm)
    intent = await engine.parse_intent("Shounen klişesi içermeyen karanlık anime")

    assert intent.media_type_filter == "ANIME"
    assert "karanlık" in intent.mood_keywords
    assert "psikolojik" in intent.target_themes
    assert "shounen klişesi" in intent.excluded_tropes
    assert intent.is_direct_title_search is False


@pytest.mark.asyncio
async def test_intent_parsing_direct_title():
    """Verify direct title query parsing."""
    mock_llm = AsyncMock(spec=LLMClient)
    mock_llm.generate_json.return_value = {
        "is_direct_title_search": True,
        "direct_title": "Fight Club",
        "media_type_filter": "MOVIE",
        "mood_keywords": [],
        "target_themes": [],
        "excluded_tropes": [],
        "reference_titles": [],
    }

    engine = RecommendationEngine(llm_client=mock_llm)
    intent = await engine.parse_intent("Fight Club izlemek istiyorum")

    assert intent.is_direct_title_search is True
    assert intent.direct_title == "Fight Club"
    assert intent.media_type_filter == "MOVIE"


@pytest.mark.asyncio
async def test_reranking_and_justification_stage_b():
    """Verify Stage B selects candidate, enforces max 2 sentences, and references taste."""
    mock_llm = AsyncMock(spec=LLMClient)
    mock_llm.generate_json.return_value = {
        "selected_external_id": "16498",
        "confidence_score": 0.95,
        "justification_text": "Altın Listendeki psikolojik gerilimi arıyorsan, nefret ettiğin shounen klişelerinden tamamen uzak bu yapım tam senin damak tadına göre. Hayatta kalma mücadelesinin acımasız gerçekliği seni ilk bölümden içine çekecek.",
    }

    engine = RecommendationEngine(llm_client=mock_llm)

    intent = UserIntentFilter(
        media_type_filter="ANIME",
        mood_keywords=["karanlık"],
        excluded_tropes=["shounen klişesi"],
    )

    candidates = [
        UnifiedMediaDTO(
            external_id="16498",
            source="ANILIST",
            title="Attack on Titan",
            release_year=2013,
            poster_url="https://s4.anilist.co/titan.jpg",
            synopsis="Mankind fight against giants...",
            genres=["Action", "Drama"],
            themes=["military", "survival"],
            base_score=8.5,
            vote_count=500000,
        ),
        UnifiedMediaDTO(
            external_id="2000",
            source="ANILIST",
            title="Generic Shounen",
            release_year=2015,
            poster_url="https://s4.anilist.co/generic.jpg",
            synopsis="Friendship saves the day...",
            genres=["Action"],
            themes=["friendship"],
            base_score=6.0,
            vote_count=1000,
        ),
    ]

    profile = UserLibraryProfile(
        gold_list=["Death Note [ANILIST] (Not: Akıl oyunları efsane)"],
        red_list=["Fairy Tail [ANILIST] (Neden: Arkadaşlık gücü klişeleri sıktı)"],
    )

    result = await engine.rerank_and_justify(
        user_prompt="Shounen klişesi içermeyen karanlık anime",
        intent=intent,
        candidates=candidates,
        user_profile=profile,
    )

    assert result.selected_external_id == "16498"
    assert result.confidence_score >= 0.9
    # Verify no synopsis keywords
    assert "Mankind fight against" not in result.justification_text
    # Verify 1 or 2 sentences max
    sentences = [s.strip() for s in result.justification_text.split(".") if s.strip()]
    assert len(sentences) <= 2


@pytest.mark.asyncio
async def test_fastapi_recommendation_endpoint():
    """Verify POST /api/v1/recommend returns 200 with structured recommendation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "prompt": "Shounen klişesi içermeyen karanlık anime",
            "limit": 5,
        }
        res = await ac.post("/api/v1/recommend", json=payload)

    assert res.status_code == 200
    data = res.json()
    assert "recommended_media" in data
    assert "justification" in data
    assert "confidence_score" in data
    assert "parsed_intent" in data
    assert data["parsed_intent"]["media_type_filter"] == "ANIME"


@pytest.mark.asyncio
async def test_fastapi_random_recommendation_endpoint():
    """Verify GET /api/v1/recommend/random returns 200 with 'Şansıma Güveniyorum' output."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/recommend/random")

    assert res.status_code == 200
    data = res.json()
    assert data["recommended_media"] is not None
    assert len(data["justification"]) > 0
    assert data["confidence_score"] > 0.0
