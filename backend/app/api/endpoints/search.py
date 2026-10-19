import logging
from typing import List, Optional
from fastapi import APIRouter, Query, status

from app.schemas.search import LiveSearchResultItem
from app.services.external.tmdb_client import (
    CURATED_POPULAR_MOVIES,
    CURATED_POPULAR_SERIES,
    TMDBClient,
)
from app.services.llm.recommendation_engine import KNOWN_ANIME_TITLES
from app.services.media_aggregator import MediaAggregatorService

logger = logging.getLogger(__name__)

router = APIRouter()
aggregator = MediaAggregatorService()

THEME_SYNONYMS = {
    "tarih": "history",
    "tarihi": "history",
    "tarihsel": "history",
    "dönem": "history",
    "orta çağ": "history",
    "antik": "history",
    "savaş": "war",
    "askeri": "war",
    "war": "war",
    "biyografi": "biography",
    "biyografik": "biography",
    "korku": "horror",
    "horror": "horror",
    "komedi": "comedy",
    "comedy": "comedy",
    "bilim kurgu": "science fiction",
    "bilimkurgu": "science fiction",
    "sci-fi": "science fiction",
    "uzay": "space",
    "romantik": "romance",
    "aşk": "romance",
    "aksiyon": "action",
    "macera": "adventure",
    "psikolojik": "psychological",
    "suç": "crime",
    "polisiye": "detective",
    "gizem": "mystery",
    "western": "western",
    "kovboy": "western",
    "belgesel": "documentary",
    "dram": "drama",
}


@router.get(
    "/live",
    response_model=List[LiveSearchResultItem],
    status_code=status.HTTP_200_OK,
    summary="Fast Live Search / Autocomplete",
    description="Performs ultra-fast parallel lookup across curated masterpieces, TMDB and AniList returning top 5 matches.",
)
async def live_search(
    q: str = Query(..., min_length=1, max_length=100, description="Keyword query for live autocomplete"),
    type: Optional[str] = Query(None, description="Optional media type filter: ALL, ANIME, MOVIE, SERIES"),
) -> List[LiveSearchResultItem]:
    """Rapid non-LLM search for interactive Omnibar dropdown."""
    clean_q = (q if isinstance(q, str) else str(q or "")).strip()
    if not clean_q:
        return []

    q_lower = clean_q.lower()
    matched_theme = None
    for k, v in THEME_SYNONYMS.items():
        if k in q_lower or q_lower == k:
            matched_theme = v
            break

    # Determine whether Anime should be searched:
    # Anime is ONLY searched if:
    # 1. The user explicitly filtered by ANIME button, OR
    # 2. The user explicitly typed an anime title or the word 'anime'
    type_val = type if isinstance(type, str) else None
    norm_type = (type_val or "").upper().strip()
    is_anime_filter = norm_type == "ANIME"
    is_movie_filter = norm_type in ("MOVIE", "FILM")
    is_series_filter = norm_type in ("SERIES", "DIZI", "TV")

    is_explicit_anime_kw = any(w in q_lower for w in ["anime", "animesi", "animeleri", "animeler", "manga", "shounen", "seinen", "isekai"])
    is_known_anime_title = any(
        title == q_lower or (len(title) >= 4 and title in q_lower)
        for title in KNOWN_ANIME_TITLES
    )

    should_search_anime = is_anime_filter or is_explicit_anime_kw or is_known_anime_title
    should_search_tmdb = not is_anime_filter

    try:
        candidates = []
        seen_keys = set()

        # 1. Run aggregator search (respecting the strict anime filter)
        online_candidates = await aggregator.search_all(
            query=clean_q,
            page=1,
            per_source_limit=5,
            enable_tmdb=should_search_tmdb,
            enable_anilist=should_search_anime,
            deduplicate_cross_source=True,
        )
        for item in online_candidates:
            key = (item.source, str(item.external_id))
            if key not in seen_keys:
                candidates.append(item)
                seen_keys.add(key)

        # 2. If user is searching by genre/theme, supplement with top-rated curated masterpieces
        if matched_theme and len(candidates) < 5 and not is_anime_filter:
            theme_keys = {matched_theme, q_lower}
            if not is_series_filter:
                for m in CURATED_POPULAR_MOVIES:
                    meta = " ".join([g.lower() for g in m.get("genres", [])] + [t.lower() for t in m.get("themes", [])])
                    if any(tk in meta for tk in theme_keys):
                        dto = TMDBClient._dict_to_dto(m, "TMDB_MOVIE")
                        key = (dto.source, str(dto.external_id))
                        if key not in seen_keys:
                            candidates.append(dto)
                            seen_keys.add(key)

            if not is_movie_filter:
                for s in CURATED_POPULAR_SERIES:
                    meta = " ".join([g.lower() for g in s.get("genres", [])] + [t.lower() for t in s.get("themes", [])])
                    if any(tk in meta for tk in theme_keys):
                        dto = TMDBClient._dict_to_dto(s, "TMDB_SERIES")
                        key = (dto.source, str(dto.external_id))
                        if key not in seen_keys:
                            candidates.append(dto)
                            seen_keys.add(key)

        # Enforce explicit tab filter on final candidates if selected
        if is_anime_filter:
            candidates = [c for c in candidates if c.source == "ANILIST"]
        elif is_movie_filter:
            candidates = [c for c in candidates if c.source == "TMDB_MOVIE"]
        elif is_series_filter:
            candidates = [c for c in candidates if c.source == "TMDB_SERIES"]

        results: List[LiveSearchResultItem] = []
        for item in candidates[:5]:
            if item.source == "ANILIST":
                media_type = "ANIME"
            elif item.source == "TMDB_SERIES":
                media_type = "SERIES"
            else:
                media_type = "MOVIE"

            results.append(
                LiveSearchResultItem(
                    id=str(item.external_id),
                    title=item.title,
                    release_year=item.release_year,
                    type=media_type,
                    poster_path=item.poster_url,
                    source=item.source,
                    base_score=item.base_score,
                    synopsis=item.synopsis,
                    genres=item.genres or [],
                )
            )

        return results
    except Exception as exc:
        logger.warning("Error during live search for query '%s': %s", clean_q, exc)
        return []
