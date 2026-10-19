import logging
import urllib.parse
from typing import Optional
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/image",
    summary="Redirect legacy TMDB image requests to global wsrv.nl CDN",
    description="Redirects legacy image.tmdb.org or proxy URLs to https://wsrv.nl CDN so the backend incurs zero image download/proxy load.",
)
async def proxy_tmdb_image(
    path: Optional[str] = Query(None, description="TMDB poster path e.g. /xyz.jpg or xyz.jpg"),
    url: Optional[str] = Query(None, description="Full TMDB image URL to redirect"),
    size: str = Query("w500", description="Image resolution size (e.g. w500, w300, original)"),
):
    """Redirects legacy TMDB poster requests to wsrv.nl global CDN."""
    if path:
        clean_path = path.lstrip("/")
        target_url = f"https://image.tmdb.org/t/p/{size}/{clean_path}"
    elif url:
        parsed = urlparse(url)
        if not parsed.scheme:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL parameter",
            )
        target_url = url
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'path' or 'url' query parameter must be provided",
        )

    if "image.tmdb.org" in target_url:
        cdn_url = f"https://wsrv.nl/?url={urllib.parse.quote(target_url, safe='')}"
    else:
        cdn_url = target_url

    return RedirectResponse(
        url=cdn_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={"Cache-Control": "public, max-age=604800, immutable"},
    )
