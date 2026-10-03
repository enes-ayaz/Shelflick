import logging
import random
from typing import Any, Dict, List, Optional
import httpx
import httpcore
from httpcore._backends.anyio import AnyIOBackend

from app.core.config import settings
from app.schemas.unified_media import UnifiedMediaDTO
from app.services.external.base_client import BaseAsyncClient

logger = logging.getLogger(__name__)

# Known fallback CloudFront IP addresses for api.themoviedb.org
CLOUDFRONT_FALLBACK_IPS = [
    "13.227.173.110",
    "13.227.173.65",
    "13.227.173.67",
    "13.227.173.106",
    "99.84.152.53",
    "99.84.152.85",
    "99.84.152.8",
    "99.84.152.32",
]

BUNNYCDN_FALLBACK_IPS = [
    "79.127.134.225",
    "143.244.56.49",
    "143.244.56.50",
    "143.244.56.51",
    "169.150.247.38",
]


class TMDBDoHBackend(AnyIOBackend):
    """Network backend that resolves api.themoviedb.org and image.tmdb.org via Cloudflare DoH,

    bypassing Turkish ISP local port 53 DNS sinkholing (127.0.0.1).
    """

    _resolved_ips: Dict[str, str] = {}

    async def _resolve_ip(self, hostname: str) -> str:
        """Queries Cloudflare DNS-over-HTTPS for the real IP of hostname."""
        if hostname in self._resolved_ips:
            return self._resolved_ips[hostname]

        try:
            async with httpx.AsyncClient(timeout=3.0) as doh_client:
                resp = await doh_client.get(
                    "https://cloudflare-dns.com/dns-query",
                    params={"name": hostname, "type": "A"},
                    headers={"accept": "application/dns-json"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    answers = data.get("Answer", [])
                    valid_ips = [
                        ans["data"]
                        for ans in answers
                        if ans.get("type") == 1 and ans.get("data")
                    ]
                    if valid_ips:
                        self._resolved_ips[hostname] = valid_ips[0]
                        logger.info("TMDB DoH resolved %s -> %s", hostname, valid_ips[0])
                        return valid_ips[0]
        except Exception as exc:
            logger.warning("Cloudflare DoH resolution failed for %s (%s)", hostname, exc)

        # Fallback to known fast IP pool
        fallback_pool = (
            BUNNYCDN_FALLBACK_IPS if "image.tmdb.org" in hostname else CLOUDFRONT_FALLBACK_IPS
        )
        ip = random.choice(fallback_pool)
        self._resolved_ips[hostname] = ip
        return ip

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: Optional[float] = None,
        local_address: Optional[str] = None,
        socket_options: Any = None,
    ) -> Any:
        if host in ("api.themoviedb.org", "image.tmdb.org"):
            resolved = await self._resolve_ip(host)
            host = resolved

        return await super().connect_tcp(
            host,
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )


class TMDBDoHTransport(httpx.AsyncHTTPTransport):
    """Custom HTTP transport utilizing TMDBDoHBackend for all socket connections."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._pool = httpcore.AsyncConnectionPool(network_backend=TMDBDoHBackend())


# Standard TMDB Genre ID to Name Mapping (Movie & TV combined)
TMDB_GENRE_MAP: Dict[int, str] = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Science Fiction",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western",
    10759: "Action & Adventure",
    10762: "Kids",
    10763: "News",
    10764: "Reality",
    10765: "Sci-Fi & Fantasy",
    10766: "Soap",
    10767: "Talk",
    10768: "War & Politics",
}


class TMDBClient(BaseAsyncClient):
    """Asynchronous client for The Movie Database (TMDB) API v3/v4."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        image_base_url: Optional[str] = None,
    ) -> None:
        token = access_token or settings.TMDB_ACCESS_TOKEN
        self.api_key = api_key or settings.TMDB_API_KEY
        self.image_base_url = (image_base_url or settings.TMDB_IMAGE_BASE_URL).rstrip("/")
        
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # Initialize with DoH transport for seamless DNS resolution
        transport = TMDBDoHTransport()

        super().__init__(
            base_url=base_url or settings.TMDB_BASE_URL,
            headers=headers,
            transport=transport,
        )

    def _build_poster_url(self, poster_path: Optional[str], size: str = "w500") -> str:
        """Constructs local image proxy URL for a TMDB poster path to bypass ISP DNS block."""
        if not poster_path:
            return ""
        clean = poster_path.lstrip("/")
        if clean.startswith("http://") or clean.startswith("https://"):
            if "image.tmdb.org" in clean:
                import urllib.parse
                return f"{settings.IMAGE_PROXY_BASE_URL}?url={urllib.parse.quote(clean, safe='')}"
            return clean
        return f"{settings.IMAGE_PROXY_BASE_URL}?path={clean}&size={size}"


    @staticmethod
    def _extract_release_year(date_str: Optional[str]) -> Optional[int]:
        """Extracts 4-digit release year from YYYY-MM-DD string."""
        if not date_str:
            return None
        try:
            return int(date_str.split("-")[0])
        except (ValueError, IndexError):
            return None

    def _item_to_dto(self, item: Dict[str, Any], default_source: Optional[str] = None) -> Optional[UnifiedMediaDTO]:
        """Maps a raw TMDB result payload into UnifiedMediaDTO."""
        media_type = item.get("media_type") or default_source
        if media_type == "movie":
            source = "TMDB_MOVIE"
            title = item.get("title") or item.get("original_title") or ""
            original_title = item.get("original_title")
            release_year = self._extract_release_year(item.get("release_date"))
        elif media_type in ("tv", "series"):
            source = "TMDB_SERIES"
            title = item.get("name") or item.get("original_name") or ""
            original_title = item.get("original_name")
            release_year = self._extract_release_year(item.get("first_air_date"))
        else:
            # Skip media_types like 'person'
            return None

        if not title:
            return None

        # Resolve genres from genre_ids or genre objects
        genres: List[str] = []
        if "genre_ids" in item and isinstance(item["genre_ids"], list):
            genres = [TMDB_GENRE_MAP[gid] for gid in item["genre_ids"] if gid in TMDB_GENRE_MAP]
        elif "genres" in item and isinstance(item["genres"], list):
            genres = [g.get("name") for g in item["genres"] if isinstance(g, dict) and g.get("name")]

        # Resolve themes from keywords
        themes: List[str] = []
        keywords_data = item.get("keywords", {})
        if isinstance(keywords_data, dict):
            # For movies: keywords.keywords, for tv: keywords.results
            kw_list = keywords_data.get("keywords") or keywords_data.get("results") or []
            if isinstance(kw_list, list):
                themes = [k.get("name") for k in kw_list if isinstance(k, dict) and k.get("name")]
        elif isinstance(keywords_data, list):
            themes = [k.get("name") for k in keywords_data if isinstance(k, dict) and k.get("name")]

        base_score = float(item.get("vote_average") or 0.0)
        vote_count = int(item.get("vote_count") or 0)
        poster_url = self._build_poster_url(item.get("poster_path"))
        synopsis = item.get("overview") or ""

        return UnifiedMediaDTO(
            external_id=str(item["id"]),
            source=source,
            title=title,
            original_title=original_title,
            release_year=release_year,
            poster_url=poster_url,
            synopsis=synopsis,
            genres=genres,
            themes=themes,
            base_score=round(base_score, 2),
            vote_count=vote_count,
        )

    async def search_multi(self, query: str, page: int = 1) -> List[UnifiedMediaDTO]:
        """Searches for movies and TV series matching the query on TMDB.

        Args:
            query: Search query text.
            page: Results page index (default: 1).

        Returns:
            List of normalized UnifiedMediaDTO items.
        """
        if not self.api_key and "Authorization" not in self._custom_headers:
            logger.info("TMDB API key or Bearer token not configured, skipping external TMDB search.")
            return []

        params: Dict[str, Any] = {
            "query": query,
            "page": page,
            "include_adult": False,
        }
        if self.api_key and "Authorization" not in self._custom_headers:
            params["api_key"] = self.api_key

        try:
            data = await self.get("search/multi", params=params)
            results = data.get("results", [])
            dtos: List[UnifiedMediaDTO] = []
            for item in results:
                dto = self._item_to_dto(item)
                if dto:
                    dtos.append(dto)
            return dtos
        except Exception as exc:
            logger.error("TMDB search_multi failed for query '%s': %s", query, exc)
            raise

    async def get_details(self, media_type: str, tmdb_id: int) -> Optional[UnifiedMediaDTO]:
        """Fetches complete details and keywords for a specific movie or TV series.

        Args:
            media_type: 'movie' or 'tv'.
            tmdb_id: Numeric TMDB ID.

        Returns:
            UnifiedMediaDTO or None if not found.
        """
        normalized_type = "tv" if media_type in ("tv", "series") else "movie"
        endpoint = f"{normalized_type}/{tmdb_id}"
        params: Dict[str, Any] = {"append_to_response": "keywords"}
        if self.api_key and "Authorization" not in self._custom_headers:
            params["api_key"] = self.api_key

        try:
            data = await self.get(endpoint, params=params)
            return self._item_to_dto(data, default_source=normalized_type)
        except Exception as exc:
            logger.error("TMDB get_details failed for %s/%s: %s", media_type, tmdb_id, exc)
            return None

    async def get_popular_posters(self, limit: int = 20) -> List[str]:
        """Fetches popular or trending media poster URLs for homepage background visuals.

        Args:
            limit: Maximum number of poster URLs to return.

        Returns:
            List of full CDN poster image URLs.
        """
        if not self.api_key and "Authorization" not in self._custom_headers:
            return []

        params: Dict[str, Any] = {"page": 1}
        if self.api_key and "Authorization" not in self._custom_headers:
            params["api_key"] = self.api_key

        try:
            data = await self.get("trending/all/day", params=params)
            results = data.get("results", [])
            posters: List[str] = []
            for item in results:
                poster_path = item.get("poster_path")
                if poster_path:
                    posters.append(self._build_poster_url(poster_path))
                if len(posters) >= limit:
                    break
            return posters
        except Exception as exc:
            logger.error("TMDB get_popular_posters failed: %s", exc)
            return []

    async def get_popular_movies(self, page: int = 1) -> List[UnifiedMediaDTO]:
        """Fetches a page of popular, high-scoring movies from TMDB."""
        if not self.api_key and "Authorization" not in self._custom_headers:
            return []

        params: Dict[str, Any] = {
            "page": page,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 200,
            "include_adult": False,
        }
        if self.api_key and "Authorization" not in self._custom_headers:
            params["api_key"] = self.api_key

        try:
            data = await self.get("discover/movie", params=params)
            results = data.get("results", [])
            dtos: List[UnifiedMediaDTO] = []
            for item in results:
                dto = self._item_to_dto(item, default_source="movie")
                if dto:
                    dtos.append(dto)
            return dtos
        except Exception as exc:
            logger.error("TMDB get_popular_movies failed: %s", exc)
            return []

    async def get_popular_series(self, page: int = 1) -> List[UnifiedMediaDTO]:
        """Fetches a page of popular, high-scoring TV series from TMDB."""
        if not self.api_key and "Authorization" not in self._custom_headers:
            return []

        params: Dict[str, Any] = {
            "page": page,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 100,
            "include_adult": False,
        }
        if self.api_key and "Authorization" not in self._custom_headers:
            params["api_key"] = self.api_key

        try:
            data = await self.get("discover/tv", params=params)
            results = data.get("results", [])
            dtos: List[UnifiedMediaDTO] = []
            for item in results:
                dto = self._item_to_dto(item, default_source="tv")
                if dto:
                    dtos.append(dto)
            return dtos
        except Exception as exc:
            logger.error("TMDB get_popular_series failed: %s", exc)
            return []

