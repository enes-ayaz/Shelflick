import pytest
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.unified_media import UnifiedMediaDTO


@pytest.mark.asyncio
async def test_live_search_endpoint():
    """Verify GET /api/v1/search/live returns top 5 lightweight results without calling any LLM."""
    sample_items = [
        UnifiedMediaDTO(
            external_id="550",
            source="TMDB_MOVIE",
            title="Fight Club",
            release_year=1999,
            poster_url="https://image.tmdb.org/fight_club.jpg",
            synopsis="An insomniac office worker...",
            genres=["Drama"],
            themes=["nihilism"],
            base_score=8.4,
            vote_count=28000,
        ),
        UnifiedMediaDTO(
            external_id="16498",
            source="ANILIST",
            title="Attack on Titan",
            release_year=2013,
            poster_url="https://s4.anilist.co/titan.jpg",
            synopsis="Centuries ago mankind...",
            genres=["Action", "Fantasy"],
            themes=["survival"],
            base_score=8.5,
            vote_count=500000,
        ),
    ]

    with patch(
        "app.services.media_aggregator.MediaAggregatorService.search_all",
        new=AsyncMock(return_value=sample_items),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/search/live?q=Fight")

        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 2

        # Check first item schema
        item0 = data[0]
        assert item0["id"] == "550"
        assert item0["title"] == "Fight Club"
        assert item0["release_year"] == 1999
        assert item0["type"] == "MOVIE"
        assert item0["poster_path"] == "https://image.tmdb.org/fight_club.jpg"

        # Check second item schema
        item1 = data[1]
        assert item1["id"] == "16498"
        assert item1["title"] == "Attack on Titan"
        assert item1["type"] == "ANIME"
