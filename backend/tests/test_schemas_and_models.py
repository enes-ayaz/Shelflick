import uuid
import pytest
from app.models.media import MediaItem, MediaSource
from app.models.user import User
from app.models.user_media import UserMedia, WatchStatus
from app.schemas.media import MediaItemCreate, MediaItemResponse
from app.schemas.rating import UserMediaCreate, UserScoreInput


def test_media_schema_validation():
    """Verify Pydantic v2 MediaItem schema validation and serialization."""
    data = {
        "external_id": "movie_550",
        "media_source": "TMDB_MOVIE",
        "title": "Fight Club",
        "original_title": "Fight Club",
        "release_year": 1999,
        "poster_url": "https://image.tmdb.org/t/p/w500/bptfVGEQuv6vDTIMVCHjJ9Dz8PX.jpg",
        "synopsis": "An insomniac office worker looking for a way to change his life...",
        "genres": ["Drama", "Thriller"],
        "themes": ["existential", "anti-consumerism"],
        "imdb_score": 8.8,
        "imdb_vote_count": 2200000,
    }

    create_schema = MediaItemCreate(**data)
    assert create_schema.title == "Fight Club"
    assert create_schema.media_source == MediaSource.TMDB_MOVIE

    # Response schema serialization
    response_data = data.copy()
    media_id = uuid.uuid4()
    response_data["id"] = media_id
    response_data["site_score"] = 9.1
    response_data["site_vote_count"] = 150

    response_schema = MediaItemResponse.model_validate(response_data)
    assert response_schema.id == media_id
    assert response_schema.site_score == 9.1
    assert response_schema.site_vote_count == 150


def test_user_score_input_validation():
    """Verify UserScoreInput boundaries."""
    valid_score = UserScoreInput(user_score=9.5)
    assert valid_score.user_score == 9.5

    with pytest.raises(Exception):
        UserScoreInput(user_score=0.9)

    with pytest.raises(Exception):
        UserScoreInput(user_score=10.1)


def test_user_media_model_instantiation():
    """Verify UserMedia model relationships and defaults."""
    user_id = uuid.uuid4()
    media_id = uuid.uuid4()

    entry = UserMedia(
        user_id=user_id,
        media_id=media_id,
        status=WatchStatus.COMPLETED,
        is_favorite=True,
        user_score=9.0,
        personal_notes="Masterpiece!",
    )

    assert entry.user_id == user_id
    assert entry.media_id == media_id
    assert entry.status == WatchStatus.COMPLETED
    assert entry.is_favorite is True
    assert entry.user_score == 9.0
