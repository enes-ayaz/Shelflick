import logging
from typing import List
from fastapi import APIRouter, Query, status

from app.schemas.search import LiveSearchResultItem
from app.services.external.tmdb_client import (
    CURATED_POPULAR_MOVIES,
    CURATED_POPULAR_SERIES,
    TMDBClient,
)
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
) -> List[LiveSearchResultItem]:
    """Rapid non-LLM search for interactive Omnibar dropdown."""
    clean_q = q.strip()
    if not clean_q:
        return []

    q_lower = clean_q.lower()
    matched_theme = None
    for k, v in THEME_SYNONYMS.items():
        if k in q_lower or q_lower == k:
            matched_theme = v
            break

    try:
        candidates = []
        seen_keys = set()

        # 1. First run aggregator search with the user's query (leveraging TMDB Discover & Turkish keywords)
        online_candidates = await aggregator.search_all(
            query=clean_q,
            page=1,
            per_source_limit=5,
            enable_tmdb=True,
            enable_anilist=True,
            deduplicate_cross_source=True,
        )
        for item in online_candidates:
            key = (item.source, str(item.external_id))
            if key not in seen_keys:
                candidates.append(item)
                seen_keys.add(key)

        # 2. If user is searching by genre/theme, supplement with top-rated curated masterpieces
        if matched_theme and len(candidates) < 5:
            theme_keys = {matched_theme, q_lower}
            for m in CURATED_POPULAR_MOVIES:
                meta = " ".join([g.lower() for g in m.get("genres", [])] + [t.lower() for t in m.get("themes", [])])
                if any(tk in meta for tk in theme_keys):
                    dto = TMDBClient._dict_to_dto(m, "TMDB_MOVIE")
                    key = (dto.source, str(dto.external_id))
                    if key not in seen_keys:
                        candidates.append(dto)
                        seen_keys.add(key)

            for s in CURATED_POPULAR_SERIES:
                meta = " ".join([g.lower() for g in s.get("genres", [])] + [t.lower() for t in s.get("themes", [])])
                if any(tk in meta for tk in theme_keys):
                    dto = TMDBClient._dict_to_dto(s, "TMDB_SERIES")
                    key = (dto.source, str(dto.external_id))
                    if key not in seen_keys:
                        candidates.append(dto)
                        seen_keys.add(key)

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
