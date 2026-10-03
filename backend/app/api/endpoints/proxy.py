import logging
from collections import OrderedDict
from typing import Optional, Tuple
from urllib.parse import urlparse
import httpx
from fastapi import APIRouter, HTTPException, Query, Response, status

from app.services.external.tmdb_client import TMDBDoHTransport

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory LRU cache for fetched poster images (stores: url -> (bytes, content_type))
MAX_CACHE_ITEMS = 1000
_IMAGE_CACHE: OrderedDict[str, Tuple[bytes, str]] = OrderedDict()

# Shared DoH transport client for proxying TMDB CDN images
_proxy_client: Optional[httpx.AsyncClient] = None


def get_proxy_client() -> httpx.AsyncClient:
    global _proxy_client
    if _proxy_client is None or _proxy_client.is_closed:
        _proxy_client = httpx.AsyncClient(
            transport=TMDBDoHTransport(),
            timeout=httpx.Timeout(12.0, connect=5.0),
            follow_redirects=True,
        )
    return _proxy_client


@router.get(
    "/image",
    summary="Proxy and cache TMDB images via DoH",
    description="Fetches TMDB images using DoH transport and serves them locally with HTTP caching headers.",
    responses={
        200: {
            "content": {"image/jpeg": {}, "image/png": {}, "image/webp": {}},
            "description": "Image binary stream",
        }
    },
)
async def proxy_tmdb_image(
    path: Optional[str] = Query(None, description="TMDB poster path e.g. /xyz.jpg or xyz.jpg"),
    url: Optional[str] = Query(None, description="Full TMDB image URL to proxy"),
    size: str = Query("w500", description="Image resolution size (e.g. w500, w300, original)"),
):
    """Fetches and streams TMDB poster images, bypassing ISP DNS sinkholes via Cloudflare DoH."""
    # 1. Determine target TMDB CDN URL
    if path:
        clean_path = path.lstrip("/")
        target_url = f"https://image.tmdb.org/t/p/{size}/{clean_path}"
    elif url:
        parsed = urlparse(url)
        if "image.tmdb.org" not in parsed.netloc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Proxy only supports image.tmdb.org sources",
            )
        target_url = url
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'path' or 'url' query parameter must be provided",
        )

    # 2. Check LRU Cache
    if target_url in _IMAGE_CACHE:
        # Move to end for LRU refresh
        _IMAGE_CACHE.move_to_end(target_url)
        image_bytes, content_type = _IMAGE_CACHE[target_url]
        return Response(
            content=image_bytes,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=604800, immutable",
                "X-Proxy-Cache": "HIT",
            },
        )

    # 3. Fetch image using DoH-enabled client
    try:
        client = get_proxy_client()
        resp = await client.get(target_url)
        if resp.status_code != 200:
            logger.warning("Failed to proxy image '%s': HTTP %s", target_url, resp.status_code)
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Upstream TMDB CDN returned HTTP {resp.status_code}",
            )

        content_type = resp.headers.get("content-type", "image/jpeg")
        image_bytes = resp.content

        # 4. Save to in-memory cache
        if len(_IMAGE_CACHE) >= MAX_CACHE_ITEMS:
            _IMAGE_CACHE.popitem(last=False)
        _IMAGE_CACHE[target_url] = (image_bytes, content_type)

        return Response(
            content=image_bytes,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=604800, immutable",
                "X-Proxy-Cache": "MISS",
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error proxying image '%s': %s", target_url, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Image proxy network failure: {str(exc)}",
        )
