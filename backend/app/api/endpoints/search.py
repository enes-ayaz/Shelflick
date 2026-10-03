import logging
from typing import List
from fastapi import APIRouter, Query, status

from app.schemas.search import LiveSearchResultItem
from app.services.media_aggregator import MediaAggregatorService

logger = logging.getLogger(__name__)

router = APIRouter()
aggregator = MediaAggregatorService()


@router.get(
    "/live",
    response_model=List[LiveSearchResultItem],
    status_code=status.HTTP_200_OK,
    summary="Fast Live Search / Autocomplete",
    description="Performs ultra-fast parallel keyword lookup across TMDB and AniList without invoking any LLM, returning top 5 matches.",
)
async def live_search(
    q: str = Query(..., min_length=1, max_length=100, description="Keyword query for live autocomplete"),
) -> List[LiveSearchResultItem]:
    """Rapid non-LLM search for interactive Omnibar dropdown."""
    clean_q = q.strip()
    if not clean_q:
        return []

    try:
        candidates = await aggregator.search_all(
            query=clean_q,
            page=1,
            per_source_limit=5,
            enable_tmdb=True,
            enable_anilist=True,
            deduplicate_cross_source=True,
        )

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
