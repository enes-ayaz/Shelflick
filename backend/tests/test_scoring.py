import pytest
from app.models.media import MediaItem, MediaSource
from app.services.scoring_service import ScoringService


def test_rule_1_zero_votes():
    """Rule 1: Community vote count == 0 -> 100% IMDb score."""
    score = ScoringService.calculate_hybrid_score(
        imdb_score=8.4,
        site_vote_count=0,
        user_avg_score=None,
    )
    assert score == 8.4


def test_rule_2_between_1_and_20_votes():
    """Rule 2: 1 <= votes <= 20 -> 70% IMDb, 30% Community."""
    # Test vote count = 1
    # IMDb: 8.0, User Avg: 10.0 -> (8.0 * 0.70) + (10.0 * 0.30) = 5.6 + 3.0 = 8.6
    score_1 = ScoringService.calculate_hybrid_score(
        imdb_score=8.0,
        site_vote_count=1,
        user_avg_score=10.0,
    )
    assert score_1 == 8.6

    # Test vote count = 20
    # IMDb: 6.0, User Avg: 9.0 -> (6.0 * 0.70) + (9.0 * 0.30) = 4.2 + 2.7 = 6.9
    score_20 = ScoringService.calculate_hybrid_score(
        imdb_score=6.0,
        site_vote_count=20,
        user_avg_score=9.0,
    )
    assert score_20 == 6.9


def test_rule_3_between_21_and_99_votes():
    """Rule 3: 21 <= votes <= 99 -> 30% IMDb, 70% Community."""
    # Test vote count = 21
    # IMDb: 8.0, User Avg: 6.0 -> (8.0 * 0.30) + (6.0 * 0.70) = 2.4 + 4.2 = 6.6
    score_21 = ScoringService.calculate_hybrid_score(
        imdb_score=8.0,
        site_vote_count=21,
        user_avg_score=6.0,
    )
    assert score_21 == 6.6

    # Test vote count = 99
    # IMDb: 5.0, User Avg: 8.0 -> (5.0 * 0.30) + (8.0 * 0.70) = 1.5 + 5.6 = 7.1
    score_99 = ScoringService.calculate_hybrid_score(
        imdb_score=5.0,
        site_vote_count=99,
        user_avg_score=8.0,
    )
    assert score_99 == 7.1


def test_rule_4_100_or_more_votes():
    """Rule 4: votes >= 100 -> 100% Community score (IMDb weight 0%)."""
    score_100 = ScoringService.calculate_hybrid_score(
        imdb_score=8.5,
        site_vote_count=100,
        user_avg_score=4.25,
    )
    assert score_100 == 4.25

    score_500 = ScoringService.calculate_hybrid_score(
        imdb_score=9.9,
        site_vote_count=500,
        user_avg_score=7.8,
    )
    assert score_500 == 7.8


def test_apply_score_in_memory_progression():
    """Test sequential rating updates on an in-memory MediaItem."""
    media = MediaItem(
        external_id="tmdb_12345",
        media_source=MediaSource.TMDB_MOVIE,
        title="Inception",
        poster_url="https://image.tmdb.org/t/p/w500/test.jpg",
        synopsis="A thief who steals corporate secrets...",
        imdb_score=8.0,
        site_vote_count=0,
        site_score=8.0,
    )

    # First vote: 10.0
    # N=1, user_avg=10.0 -> (8.0 * 0.70) + (10.0 * 0.30) = 8.6
    new_score = ScoringService.apply_score_in_memory(media, 10.0)
    assert media.site_vote_count == 1
    assert new_score == 8.6
    assert media.site_score == 8.6

    # Second vote: 6.0
    # user_avg becomes (10.0 + 6.0) / 2 = 8.0
    # N=2 -> (8.0 * 0.70) + (8.0 * 0.30) = 8.0
    new_score_2 = ScoringService.apply_score_in_memory(media, 6.0)
    assert media.site_vote_count == 2
    assert new_score_2 == 8.0
    assert media.site_score == 8.0


def test_score_validation_bounds():
    """Ensure invalid scores outside 1.0 - 10.0 raise ValueError."""
    media = MediaItem(
        external_id="tmdb_1",
        media_source=MediaSource.TMDB_MOVIE,
        title="Test",
        poster_url="https://example.com/poster.jpg",
        synopsis="Test synopsis",
        imdb_score=7.0,
        site_vote_count=0,
    )

    with pytest.raises(ValueError):
        ScoringService.apply_score_in_memory(media, 0.5)

    with pytest.raises(ValueError):
        ScoringService.apply_score_in_memory(media, 10.5)
