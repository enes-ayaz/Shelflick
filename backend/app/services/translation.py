import asyncio
import logging
import re
import urllib.parse
from typing import Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

TURKISH_CHARS = set("çğıöşüÇĞİÖŞÜ")
ENGLISH_MARKER_WORDS = {
    "the", "and", "of", "in", "to", "a", "is", "was", "for", "with",
    "by", "an", "his", "her", "their", "when", "after", "who", "from",
    "into", "that", "this", "which", "about", "starring", "series", "film",
    "story", "lives", "years", "during", "takes", "place"
}


def is_english_or_needs_translation(text: Optional[str]) -> bool:
    """Returns True if the synopsis is likely English and lacks Turkish characters."""
    if not text or len(text.strip()) < 10:
        return False
    clean = text.strip()
    turkish_char_count = sum(1 for c in clean if c in TURKISH_CHARS)
    if turkish_char_count >= 2:
        return False

    words = set(re.findall(r"\b[a-zA-Z]+\b", clean.lower()))
    english_hits = len(words.intersection(ENGLISH_MARKER_WORDS))
    return english_hits >= 2


async def translate_to_turkish(text: str) -> str:
    """Translates text to natural Turkish using Google Translate API."""
    if not text or not text.strip():
        return text

    clean_text = text.strip()
    try:
        encoded_q = urllib.parse.quote(clean_text[:1800])
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=tr&dt=t&q={encoded_q}"
        async with httpx.AsyncClient(timeout=3.5) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                data = resp.json()
                translated = "".join(
                    [part[0] for part in data[0] if part and len(part) > 0 and part[0]]
                )
                if translated and len(translated.strip()) > 5:
                    return translated.strip()
    except Exception as exc:
        logger.debug("Fast translation to Turkish failed: %s", exc)

    return text


async def resolve_turkish_synopsis(
    synopsis: Optional[str],
    external_id: Optional[str] = None,
    source: Optional[str] = None,
    title: Optional[str] = None,
) -> str:
    """Ensures media synopsis is provided in high-quality Turkish.

    1. Checks if synopsis is already in Turkish.
    2. Queries TMDB API for official Turkish overview if it's a TMDB item.
    3. Translates English synopsis to Turkish.
    """
    raw_synopsis = (synopsis or "").strip()

    # If it's already in Turkish, return immediately
    if raw_synopsis and not is_english_or_needs_translation(raw_synopsis):
        return raw_synopsis

    # 1. Try official TMDB tr-TR overview if it's a TMDB item
    if external_id and settings.TMDB_API_KEY:
        clean_id = str(external_id).strip()
        if clean_id.isdigit():
            mtype = "tv" if source in ("TMDB_SERIES", "tv", "series") else "movie"
            try:
                async with httpx.AsyncClient(timeout=2.5) as client:
                    resp = await client.get(
                        f"https://api.themoviedb.org/3/{mtype}/{clean_id}",
                        params={"api_key": settings.TMDB_API_KEY, "language": "tr-TR"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        tr_overview = (data.get("overview") or "").strip()
                        if tr_overview and len(tr_overview) > 15:
                            return tr_overview
            except Exception as e:
                logger.debug("TMDB Turkish overview query failed for %s: %s", clean_id, e)

    # 2. Translate English synopsis to Turkish
    if raw_synopsis:
        translated = await translate_to_turkish(raw_synopsis)
        if translated and translated != raw_synopsis:
            return translated

    return raw_synopsis or (f"{title or 'Bu yapım'} hakkında Türkçe açıklama yakında eklenecektir.")
