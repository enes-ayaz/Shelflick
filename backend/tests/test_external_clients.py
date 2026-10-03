import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from app.schemas.unified_media import UnifiedMediaDTO
from app.services.external.anilist_client import AniListClient
from app.services.external.tmdb_client import TMDBClient
from app.services.media_aggregator import MediaAggregatorService


@pytest.mark.asyncio
async def test_tmdb_dto_mapping():
    """Verify TMDB search response is parsed accurately into UnifiedMediaDTO."""
    client = TMDBClient(access_token="fake_token_123")
    
    mock_payload = {
        "results": [
            {
                "id": 550,
                "media_type": "movie",
                "title": "Fight Club",
                "original_title": "Fight Club",
                "release_date": "1999-10-15",
                "poster_path": "/bptfVGEQuv6vDTIMVCHjJ9Dz8PX.jpg",
                "overview": "An insomniac office worker...",
                "genre_ids": [18, 53],  # Drama, Thriller
                "vote_average": 8.433,
                "vote_count": 26000,
            },
            {
                "id": 1399,
                "media_type": "tv",
                "name": "Game of Thrones",
                "original_name": "Game of Thrones",
                "first_air_date": "2011-04-17",
                "poster_path": "/u3bZgnGQ9T01sWNhyveQz0wH0Hl.jpg",
                "overview": "Seven noble families fight for control...",
                "genre_ids": [10765, 18],  # Sci-Fi & Fantasy, Drama
                "vote_average": 8.45,
                "vote_count": 23000,
            },
            {
                "id": 9999,
                "media_type": "person",  # Should be filtered out
                "name": "Brad Pitt",
            },
        ]
    }

    with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_payload
        results = await client.search_multi("fight club")

    assert len(results) == 2

    # Movie assertion
    movie = results[0]
    assert movie.external_id == "550"
    assert movie.source == "TMDB_MOVIE"
    assert movie.title == "Fight Club"
    assert movie.release_year == 1999
    assert movie.poster_url == "https://image.tmdb.org/t/p/w500/bptfVGEQuv6vDTIMVCHjJ9Dz8PX.jpg"
    assert "Drama" in movie.genres
    assert "Thriller" in movie.genres
    assert movie.base_score == 8.43
    assert movie.vote_count == 26000

    # TV Series assertion
    tv = results[1]
    assert tv.external_id == "1399"
    assert tv.source == "TMDB_SERIES"
    assert tv.title == "Game of Thrones"
    assert tv.release_year == 2011
    assert "Sci-Fi & Fantasy" in tv.genres
    assert tv.base_score == 8.45


@pytest.mark.asyncio
async def test_tmdb_popular_posters():
    """Verify popular poster URLs extraction."""
    client = TMDBClient(api_key="mock_tmdb_key_123")
    mock_payload = {
        "results": [
            {"poster_path": "/poster1.jpg"},
            {"poster_path": "/poster2.jpg"},
            {"poster_path": None},  # should be ignored
        ]
    }

    with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_payload
        posters = await client.get_popular_posters(limit=2)

    assert len(posters) == 2
    assert posters[0] == "https://image.tmdb.org/t/p/w500/poster1.jpg"
    assert posters[1] == "https://image.tmdb.org/t/p/w500/poster2.jpg"


@pytest.mark.asyncio
async def test_anilist_dto_mapping():
    """Verify AniList GraphQL response normalization and HTML cleanup."""
    client = AniListClient()

    mock_payload = {
        "data": {
            "Page": {
                "media": [
                    {
                        "id": 16498,
                        "title": {
                            "english": "Attack on Titan",
                            "romaji": "Shingeki no Kyojin",
                            "native": "進撃の巨人",
                        },
                        "description": "Centuries ago, mankind was almost slaughtered...<br><br><i>Titans</i> attacked.",
                        "startDate": {"year": 2013},
                        "coverImage": {
                            "large": "https://s4.anilist.co/file/anilistcdn/media/anime/cover/medium/bx16498.jpg"
                        },
                        "genres": ["Action", "Drama", "Fantasy"],
                        "tags": [
                            {"name": "Post-Apocalyptic", "rank": 95, "isMediaSpoiler": False},
                            {"name": "Gore", "rank": 85, "isMediaSpoiler": False},
                            {"name": "Secret Spoiler", "rank": 90, "isMediaSpoiler": True},  # filtered
                            {"name": "Low Rank", "rank": 30, "isMediaSpoiler": False},  # filtered
                        ],
                        "averageScore": 84,  # -> 8.4
                        "popularity": 550000,
                    }
                ]
            }
        }
    }

    with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_payload
        results = await client.search_anime("titan")

    assert len(results) == 1
    anime = results[0]
    assert anime.external_id == "16498"
    assert anime.source == "ANILIST"
    assert anime.title == "Attack on Titan"
    assert anime.original_title == "進撃の巨人"
    assert anime.release_year == 2013
    assert anime.base_score == 8.4
    assert anime.vote_count == 550000
    assert "Titans attacked." in anime.synopsis
    assert "<br>" not in anime.synopsis
    assert "post-apocalyptic" in anime.themes
    assert "gore" in anime.themes
    assert "secret spoiler" not in anime.themes
    assert "low rank" not in anime.themes


@pytest.mark.asyncio
async def test_media_aggregator_parallel_and_deduplication():
    """Verify parallel search via gather, graceful failure handling, and deduplication."""
    mock_tmdb = AsyncMock(spec=TMDBClient)
    mock_anilist = AsyncMock(spec=AniListClient)

    dto1 = UnifiedMediaDTO(
        external_id="101",
        source="TMDB_MOVIE",
        title="Spirited Away",
        release_year=2001,
        poster_url="https://image.tmdb.org/t/p/w500/spirited.jpg",
        synopsis="A girl wandering into a world of spirits...",
        genres=["Animation", "Family"],
        base_score=8.5,
        vote_count=15000,
    )
    # Duplicate item in TMDB
    dto1_duplicate = dto1.model_copy()

    dto2 = UnifiedMediaDTO(
        external_id="199",
        source="ANILIST",
        title="Spirited Away",
        release_year=2001,
        poster_url="https://s4.anilist.co/spirited.jpg",
        synopsis="Sen to Chihiro no Kamikakushi...",
        genres=["Supernatural"],
        base_score=8.7,
        vote_count=200000,
    )

    mock_tmdb.search_multi.return_value = [dto1, dto1_duplicate]
    mock_anilist.search_anime.return_value = [dto2]

    aggregator = MediaAggregatorService(tmdb_client=mock_tmdb, anilist_client=mock_anilist)
    results = await aggregator.search_all("spirited away")

    # Both TMDB and AniList should be called in parallel
    mock_tmdb.search_multi.assert_awaited_once_with(query="spirited away", page=1)
    mock_anilist.search_anime.assert_awaited_once_with(query="spirited away", page=1, per_page=20)

    # Duplicate dto1 was eliminated; results are sorted by vote_count descending (dto2 first, then dto1)
    assert len(results) == 2
    assert results[0].source == "ANILIST"
    assert results[1].source == "TMDB_MOVIE"


@pytest.mark.asyncio
async def test_media_aggregator_graceful_provider_failure():
    """Verify aggregator returns partial results if one provider encounters an exception."""
    mock_tmdb = AsyncMock(spec=TMDBClient)
    mock_anilist = AsyncMock(spec=AniListClient)

    # TMDB fails with connection timeout
    mock_tmdb.search_multi.side_effect = Exception("TMDB connection timed out")

    # AniList succeeds
    dto_anime = UnifiedMediaDTO(
        external_id="999",
        source="ANILIST",
        title="Cowboy Bebop",
        release_year=1998,
        poster_url="https://s4.anilist.co/bebop.jpg",
        synopsis="Space bounty hunters...",
        genres=["Action", "Sci-Fi"],
        base_score=8.9,
        vote_count=300000,
    )
    mock_anilist.search_anime.return_value = [dto_anime]

    aggregator = MediaAggregatorService(tmdb_client=mock_tmdb, anilist_client=mock_anilist)
    results = await aggregator.search_all("cowboy bebop")

    assert len(results) == 1
    assert results[0].title == "Cowboy Bebop"
