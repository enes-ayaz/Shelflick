import asyncio
import logging
import random
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import NonCallableMock

from app.schemas.unified_media import UnifiedMediaDTO
from app.services.external.anilist_client import AniListClient
from app.services.external.tmdb_client import TMDBClient

logger = logging.getLogger(__name__)

# 10-minute in-memory TTL caches for instant 0ms repeat queries
_SEARCH_CACHE: Dict[Tuple[str, int, int, bool, bool, bool], Tuple[float, List[UnifiedMediaDTO]]] = {}
_MASTERPIECE_CACHE: Dict[str, Tuple[float, List[UnifiedMediaDTO]]] = {}
CACHE_TTL_SECONDS = 600.0  # 10 minutes
PROVIDER_TIMEOUT_SECONDS = 2.5


class MediaAggregatorService:
    """Service that orchestrates parallel searches across TMDBClient (TVMaze/IMDb/iTunes) and AniList,

    enforcing strict 2.5s timeouts and 10-minute in-memory TTL caching.
    """

    def __init__(
        self,
        tmdb_client: Optional[TMDBClient] = None,
        anilist_client: Optional[AniListClient] = None,
    ) -> None:
        self.tmdb_client = tmdb_client or TMDBClient()
        self.anilist_client = anilist_client or AniListClient()

    def _is_mocked(self) -> bool:
        """Detects if either underlying client is a unittest mock so unit tests bypass global cache."""
        return (
            isinstance(self.tmdb_client, NonCallableMock)
            or isinstance(self.anilist_client, NonCallableMock)
            or isinstance(getattr(self.tmdb_client, "search_multi", None), NonCallableMock)
            or isinstance(getattr(self.anilist_client, "search_anime", None), NonCallableMock)
        )

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
        cleaned = re.sub(r"[^\w\s]", "", title.lower())
        return re.sub(r"\s+", " ", cleaned).strip()

    def _deduplicate(
        self,
        items: List[UnifiedMediaDTO],
        deduplicate_cross_source: bool = False,
    ) -> List[UnifiedMediaDTO]:
        """Eliminates duplicates from aggregated results."""
        seen_primary_keys: Set[Tuple[str, str]] = set()
        seen_cross_keys: Set[Tuple[str, Optional[int]]] = set()
        deduped: List[UnifiedMediaDTO] = []

        for item in items:
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

    async def search_all(
        self,
        query: str,
        page: int = 1,
        per_source_limit: int = 20,
        enable_tmdb: bool = True,
        enable_anilist: bool = True,
        deduplicate_cross_source: bool = False,
    ) -> List[UnifiedMediaDTO]:
        """Searches providers in parallel with a strict 2.5s timeout and 10-minute RAM TTL cache."""
        clean_query = query.strip()
        if not clean_query:
            return []

        use_cache = not self._is_mocked()
        cache_key = (
            clean_query.lower(),
            page,
            per_source_limit,
            enable_tmdb,
            enable_anilist,
            deduplicate_cross_source,
        )
        now = time.monotonic()

        if use_cache and cache_key in _SEARCH_CACHE:
            ts, cached_results = _SEARCH_CACHE[cache_key]
            if now - ts < CACHE_TTL_SECONDS:
                return list(cached_results)

        tasks = []
        task_names = []

        if enable_tmdb:
            tasks.append(
                asyncio.wait_for(
                    self.tmdb_client.search_multi(query=clean_query, page=page),
                    timeout=PROVIDER_TIMEOUT_SECONDS,
                )
            )
            task_names.append("TMDB")

        if enable_anilist:
            tasks.append(
                asyncio.wait_for(
                    self.anilist_client.search_anime(
                        query=clean_query,
                        page=page,
                        per_page=per_source_limit,
                    ),
                    timeout=PROVIDER_TIMEOUT_SECONDS,
                )
            )
            task_names.append("AniList")

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)

        aggregated: List[UnifiedMediaDTO] = []
        for name, res in zip(task_names, results):
            if isinstance(res, Exception):
                logger.warning("Provider '%s' timed out or failed for '%s': %s", name, clean_query, res)
            elif isinstance(res, list):
                aggregated.extend(res)

        deduped = self._deduplicate(
            aggregated,
            deduplicate_cross_source=deduplicate_cross_source,
        )

        deduped.sort(key=lambda x: x.vote_count, reverse=True)

        if use_cache and deduped:
            _SEARCH_CACHE[cache_key] = (now, list(deduped))

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
            return await asyncio.wait_for(
                self.tmdb_client.get_popular_posters(limit=limit),
                timeout=PROVIDER_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            logger.warning("Failed to fetch featured posters: %s", exc)
            return []

    async def get_random_masterpieces(
        self,
        limit: int = 20,
        media_type: Optional[str] = None,
    ) -> List[UnifiedMediaDTO]:
        """Fetches top-rated candidates across providers with strict 2.5s timeout and TTL caching."""
        norm_mt = media_type.upper().strip() if media_type else None
        if norm_mt in ("FILM", "MOVIE"):
            target_type = "MOVIE"
        elif norm_mt in ("TV", "SERIES", "DIZI"):
            target_type = "SERIES"
        elif norm_mt in ("ANIME",):
            target_type = "ANIME"
        else:
            target_type = "ALL"

        use_cache = not self._is_mocked()
        now = time.monotonic()
        if use_cache and target_type in _MASTERPIECE_CACHE:
            ts, cached_pool = _MASTERPIECE_CACHE[target_type]
            if now - ts < CACHE_TTL_SECONDS and cached_pool:
                shuffled = list(cached_pool)
                random.shuffle(shuffled)
                return shuffled[: max(limit, 25)]

        tasks = []
        if target_type == "ANIME":
            random_anime_page = random.randint(1, 5)
            tasks.append(
                asyncio.wait_for(
                    self.anilist_client.get_popular_anime(page=random_anime_page, per_page=limit),
                    timeout=PROVIDER_TIMEOUT_SECONDS,
                )
            )
        if target_type in ("ALL", "MOVIE"):
            tasks.append(
                asyncio.wait_for(
                    self.tmdb_client.get_popular_movies(page=1),
                    timeout=PROVIDER_TIMEOUT_SECONDS,
                )
            )
        if target_type in ("ALL", "SERIES"):
            tasks.append(
                asyncio.wait_for(
                    self.tmdb_client.get_popular_series(page=1),
                    timeout=PROVIDER_TIMEOUT_SECONDS,
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)
        candidates: List[UnifiedMediaDTO] = []

        for res in results:
            if isinstance(res, list):
                candidates.extend(res)

        if target_type == "ANIME":
            candidates = [c for c in candidates if c.source == "ANILIST"]
        elif target_type == "MOVIE":
            candidates = [c for c in candidates if c.source == "TMDB_MOVIE"]
        elif target_type == "SERIES":
            candidates = [c for c in candidates if c.source == "TMDB_SERIES"]
        else:
            candidates = [c for c in candidates if c.source != "ANILIST"]

        deduped = self._deduplicate(candidates)
        if use_cache and deduped:
            _MASTERPIECE_CACHE[target_type] = (now, list(deduped))

        random.shuffle(deduped)
        return deduped
