import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from app.schemas.unified_media import UnifiedMediaDTO
from app.services.external.anilist_client import AniListClient
from app.services.external.tmdb_client import TMDBClient

logger = logging.getLogger(__name__)


class MediaAggregatorService:
    """Service that orchestrates parallel searches across TMDB and AniList,

    deduplicating and normalizing incoming records into UnifiedMediaDTO objects.
    """

    def __init__(
        self,
        tmdb_client: Optional[TMDBClient] = None,
        anilist_client: Optional[AniListClient] = None,
    ) -> None:
        self.tmdb_client = tmdb_client or TMDBClient()
        self.anilist_client = anilist_client or AniListClient()

    async def close(self) -> None:
        """Closes all underlying HTTP client connections."""
        await self.tmdb_client.close()
        await self.anilist_client.close()

    async def __aenter__(self) -> "MediaAggregatorService":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    @staticmethod
    def _normalize_title_key(title: str) -> str:
        """Cleanses title for fuzzy duplicate detection."""
        # Convert to lower, strip punctuation and extra spaces
        cleaned = re.sub(r"[^\w\s]", "", title.lower())
        return re.sub(r"\s+", " ", cleaned).strip()

    def _deduplicate(
        self,
        items: List[UnifiedMediaDTO],
        deduplicate_cross_source: bool = False,
    ) -> List[UnifiedMediaDTO]:
        """Eliminates duplicates from aggregated results.

        Args:
            items: Combined list of media DTOs.
            deduplicate_cross_source: If True, merges/deduplicates titles matching
                normalized title and release year across TMDB and AniList.

        Returns:
            Deduplicated list of UnifiedMediaDTO items.
        """
        seen_primary_keys: Set[Tuple[str, str]] = set()
        seen_cross_keys: Set[Tuple[str, Optional[int]]] = set()
        deduped: List[UnifiedMediaDTO] = []

        for item in items:
            # Primary uniqueness: (source, external_id)
            primary_key = (item.source, item.external_id)
            if primary_key in seen_primary_keys:
                continue
            seen_primary_keys.add(primary_key)

            if deduplicate_cross_source:
                norm_title = self._normalize_title_key(item.title)
                cross_key = (norm_title, item.release_year)
                if norm_title and cross_key in seen_cross_keys:
                    logger.debug("Deduplicated cross-source item: %s (%s)", item.title, item.source)
                    continue
                seen_cross_keys.add(cross_key)

            deduped.append(item)

        return deduped

    @retry(
        retry=retry_if_exception_type((asyncio.TimeoutError, ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2.0),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def search_all(
        self,
        query: str,
        page: int = 1,
        per_source_limit: int = 20,
        enable_tmdb: bool = True,
        enable_anilist: bool = True,
        deduplicate_cross_source: bool = False,
    ) -> List[UnifiedMediaDTO]:
        """Searches TMDB and AniList in parallel using asyncio.gather.

        Combines, deduplicates, and sorts records by vote/popularity metric.

        Args:
            query: User search text.
            page: Pagination page number (default: 1).
            per_source_limit: Results count requested per provider.
            enable_tmdb: Whether to query TMDB.
            enable_anilist: Whether to query AniList.
            deduplicate_cross_source: Whether to filter cross-provider title collisions.

        Returns:
            Consolidated list of UnifiedMediaDTO items.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        tasks = []
        task_names = []

        if enable_tmdb:
            tasks.append(self.tmdb_client.search_multi(query=clean_query, page=page))
            task_names.append("TMDB")

        if enable_anilist:
            tasks.append(
                self.anilist_client.search_anime(
                    query=clean_query,
                    page=page,
                    per_page=per_source_limit,
                )
            )
            task_names.append("AniList")

        if not tasks:
            return []

        # Run both tasks concurrently; catch exceptions to prevent one failure from halting all results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        aggregated: List[UnifiedMediaDTO] = []
        for name, res in zip(task_names, results):
            if isinstance(res, Exception):
                logger.warning("Provider '%s' failed during search for '%s': %s", name, clean_query, res)
            elif isinstance(res, list):
                aggregated.extend(res)

        # Deduplicate results
        deduped = self._deduplicate(
            aggregated,
            deduplicate_cross_source=deduplicate_cross_source,
        )

        # Sort combined results primarily by vote_count / popularity descending
        deduped.sort(key=lambda x: x.vote_count, reverse=True)

        logger.info(
            "Aggregator search completed for '%s': retrieved %s unique items (TMDB=%s, AniList=%s)",
            clean_query,
            len(deduped),
            enable_tmdb,
            enable_anilist,
        )
        return deduped

    async def get_homepage_featured_posters(self, limit: int = 15) -> List[str]:
        """Convenience method to retrieve popular background posters for discovery screens."""
        try:
            return await self.tmdb_client.get_popular_posters(limit=limit)
        except Exception as exc:
            logger.warning("Failed to fetch featured posters: %s", exc)
            return []

    async def get_random_masterpieces(
        self,
        limit: int = 20,
        media_type: Optional[str] = None,
    ) -> List[UnifiedMediaDTO]:
        """Fetches top-rated candidates across providers using randomized pagination.

        Guarantees that each invocation surfaces a distinct, diverse pool of high-scoring works
        respecting the optional media_type constraint (movie, series, anime, or all).
        """
        import random

        norm_mt = media_type.upper().strip() if media_type else None
        if norm_mt in ("FILM", "MOVIE"):
            target_type = "MOVIE"
        elif norm_mt in ("TV", "SERIES", "DIZI"):
            target_type = "SERIES"
        elif norm_mt in ("ANIME",):
            target_type = "ANIME"
        else:
            target_type = "ALL"

        tasks = []
        if target_type in ("ALL", "ANIME"):
            random_anime_page = random.randint(1, 15)
            tasks.append(self.anilist_client.get_popular_anime(page=random_anime_page, per_page=limit))
        if target_type in ("ALL", "MOVIE"):
            random_movie_page = random.randint(1, 10)
            tasks.append(self.tmdb_client.get_popular_movies(page=random_movie_page))
        if target_type in ("ALL", "SERIES"):
            random_tv_page = random.randint(1, 10)
            tasks.append(self.tmdb_client.get_popular_series(page=random_tv_page))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        candidates: List[UnifiedMediaDTO] = []

        for res in results:
            if isinstance(res, list):
                candidates.extend(res)

        if not candidates:
            # Fallback to search if popular queries fail
            if target_type == "ANIME":
                fallback_terms = ["death note", "hunter x hunter", "monster", "steins gate", "attack on titan", "vinland saga", "berserk", "cowboy bebop"]
            elif target_type == "MOVIE":
                fallback_terms = ["matrix", "interstellar", "inception", "fight club", "pulp fiction", "parasite"]
            elif target_type == "SERIES":
                fallback_terms = ["breaking bad", "dark", "better call saul", "severance", "stranger things"]
            else:
                fallback_terms = ["death note", "hunter x hunter", "monster", "steins gate", "attack on titan", "matrix", "interstellar", "inception", "breaking bad", "dark"]
            term = random.choice(fallback_terms)
            candidates = await self.search(
                query=term,
                enable_tmdb=(target_type in ("ALL", "MOVIE", "SERIES")),
                enable_anilist=(target_type in ("ALL", "ANIME")),
            )

        # Enforce exact type filter if specified
        if target_type == "ANIME":
            candidates = [c for c in candidates if c.source == "ANILIST"]
        elif target_type == "MOVIE":
            candidates = [c for c in candidates if c.source == "TMDB_MOVIE"]
        elif target_type == "SERIES":
            candidates = [c for c in candidates if c.source == "TMDB_SERIES"]

        deduped = self._deduplicate(candidates)
        random.shuffle(deduped)
        return deduped

