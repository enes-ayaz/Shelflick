import logging
import random
import re
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.schemas.unified_media import UnifiedMediaDTO
from app.services.external.base_client import BaseAsyncClient

logger = logging.getLogger(__name__)

# GraphQL query for searching anime on AniList
ANIME_SEARCH_QUERY = """
query SearchAnime($search: String, $page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo {
      total
      currentPage
      hasNextPage
    }
    media(search: $search, type: ANIME, sort: [SEARCH_MATCH, POPULARITY_DESC]) {
      id
      title {
        romaji
        english
        native
        userPreferred
      }
      description(asHtml: false)
      startDate {
        year
        month
        day
      }
      coverImage {
        extraLarge
        large
        medium
      }
      genres
      tags {
        id
        name
        description
        category
        rank
        isMediaSpoiler
      }
      averageScore
      popularity
    }
  }
}
"""

# GraphQL query for single media details by AniList ID
ANIME_DETAILS_QUERY = """
query GetAnimeDetails($id: Int) {
  Media(id: $id, type: ANIME) {
    id
    title {
      romaji
      english
      native
      userPreferred
    }
    description(asHtml: false)
    startDate {
      year
    }
    coverImage {
      extraLarge
      large
    }
    genres
    tags {
      name
      rank
      isMediaSpoiler
    }
    averageScore
    popularity
  }
}
"""

# GraphQL query for top-rated popular anime with pagination
ANIME_POPULAR_QUERY = """
query GetPopularAnime($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo {
      total
      currentPage
      hasNextPage
    }
    media(type: ANIME, sort: [SCORE_DESC, POPULARITY_DESC]) {
      id
      title {
        romaji
        english
        native
        userPreferred
      }
      description(asHtml: false)
      startDate {
        year
      }
      coverImage {
        extraLarge
        large
        medium
      }
      genres
      tags {
        name
        rank
        isMediaSpoiler
      }
      averageScore
      popularity
    }
  }
}
"""


class AniListClient(BaseAsyncClient):
    """Asynchronous client for AniList GraphQL API."""

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
    ) -> None:
        super().__init__(
            base_url=endpoint_url or settings.ANILIST_GRAPHQL_URL,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    @staticmethod
    def _strip_html(text_content: Optional[str]) -> str:
        """Strips HTML tags and unescapes common entities from description."""
        if not text_content:
            return ""
        # Remove HTML tags like <br>, <i>, </i>
        clean = re.sub(r"<[^>]+>", " ", text_content)
        # Normalize excessive whitespace
        return re.sub(r"\s+", " ", clean).strip()

    def _item_to_dto(self, media: Dict[str, Any]) -> Optional[UnifiedMediaDTO]:
        """Converts raw AniList media payload to UnifiedMediaDTO."""
        if not media or not media.get("id"):
            return None

        # Resolve title: prioritize english, then userPreferred, then romaji, then native
        title_dict = media.get("title") or {}
        title = (
            title_dict.get("english")
            or title_dict.get("userPreferred")
            or title_dict.get("romaji")
            or title_dict.get("native")
            or ""
        )
        if not title:
            return None

        original_title = title_dict.get("native") or title_dict.get("romaji")

        # Resolve release year
        start_date = media.get("startDate") or {}
        release_year = start_date.get("year")

        # Resolve poster image
        cover_image = media.get("coverImage") or {}
        poster_url = cover_image.get("large") or cover_image.get("extraLarge") or cover_image.get("medium") or ""

        # Clean synopsis
        synopsis = self._strip_html(media.get("description"))

        # Genres
        genres = [str(g) for g in media.get("genres", []) if g]

        # Themes & thematic tags (filter out spoilers, rank >= 50 for relevance)
        themes: List[str] = []
        raw_tags = media.get("tags") or []
        for tag in raw_tags:
            if isinstance(tag, dict):
                is_spoiler = tag.get("isMediaSpoiler", False)
                rank = tag.get("rank", 0)
                name = tag.get("name")
                if name and not is_spoiler and (rank is None or rank >= 50):
                    themes.append(name.lower())

        # AniList score is out of 100 (e.g. 84) -> convert to 0.0 - 10.0 scale
        raw_score = media.get("averageScore")
        base_score = round(float(raw_score) / 10.0, 2) if raw_score is not None else 0.0
        vote_count = int(media.get("popularity") or 0)

        return UnifiedMediaDTO(
            external_id=str(media["id"]),
            source="ANILIST",
            title=title,
            original_title=original_title,
            release_year=release_year,
            poster_url=poster_url,
            synopsis=synopsis,
            genres=genres,
            themes=themes,
            base_score=base_score,
            vote_count=vote_count,
        )

    async def search_anime(self, query: str, page: int = 1, per_page: int = 20) -> List[UnifiedMediaDTO]:
        """Executes a GraphQL search query for anime on AniList.

        Args:
            query: Title keyword to search.
            page: Pagination page (default: 1).
            per_page: Number of results per page (default: 20).

        Returns:
            List of normalized UnifiedMediaDTO objects.
        """
        payload = {
            "query": ANIME_SEARCH_QUERY,
            "variables": {
                "search": query,
                "page": page,
                "perPage": per_page,
            },
        }

        try:
            data = await self.post("", json_data=payload)
            page_data = data.get("data", {}).get("Page", {})
            media_list = page_data.get("media", [])
            
            dtos: List[UnifiedMediaDTO] = []
            for item in media_list:
                dto = self._item_to_dto(item)
                if dto:
                    dtos.append(dto)
            return dtos
        except Exception as exc:
            logger.error("AniList search_anime failed for query '%s': %s", query, exc)
            raise

    async def get_details(self, anilist_id: int) -> Optional[UnifiedMediaDTO]:
        """Fetches detailed information for a single anime title by ID.

        Args:
            anilist_id: AniList numeric media ID.

        Returns:
            UnifiedMediaDTO or None if not found.
        """
        payload = {
            "query": ANIME_DETAILS_QUERY,
            "variables": {"id": anilist_id},
        }

        try:
            data = await self.post("", json_data=payload)
            media = data.get("data", {}).get("Media")
            return self._item_to_dto(media) if media else None
        except Exception as exc:
            logger.error("AniList get_details failed for ID %s: %s", anilist_id, exc)
            return None

    async def get_popular_anime(
        self,
        page: Optional[int] = None,
        per_page: int = 20,
    ) -> List[UnifiedMediaDTO]:
        """Fetches a paginated batch of top-rated popular anime with randomized page support.

        Args:
            page: Specific page number or None to randomly select among top pages.
            per_page: Batch size per page (default: 20).

        Returns:
            List of normalized UnifiedMediaDTO objects.
        """
        target_page = page if page is not None else random.randint(1, 15)
        payload = {
            "query": ANIME_POPULAR_QUERY,
            "variables": {
                "page": target_page,
                "perPage": per_page,
            },
        }

        try:
            data = await self.post("", json_data=payload)
            page_data = data.get("data", {}).get("Page", {})
            media_list = page_data.get("media", [])
            dtos: List[UnifiedMediaDTO] = []
            for item in media_list:
                dto = self._item_to_dto(item)
                if dto:
                    dtos.append(dto)
            return dtos
        except Exception as exc:
            logger.error("AniList get_popular_anime failed (page %s): %s", target_page, exc)
            return []
