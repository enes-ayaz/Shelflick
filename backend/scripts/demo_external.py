import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.external.anilist_client import AniListClient
from app.services.media_aggregator import MediaAggregatorService


async def test_live_anilist():
    print("Testing live AniList GraphQL API...")
    client = AniListClient()
    try:
        results = await client.search_anime("Steins Gate", per_page=2)
        for r in results:
            print(f"-> Found: {r.title} ({r.release_year}) | Score: {r.base_score} | Source: {r.source}")
            print(f"   Poster: {r.poster_url}")
            print(f"   Genres: {r.genres}")
            print(f"   Themes: {r.themes[:5]}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_live_anilist())
