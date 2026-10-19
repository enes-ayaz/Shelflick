import sys
import httpx
sys.path.insert(0, ".")
from app.services.external.tmdb_client import CURATED_POPULAR_SERIES, CURATED_POPULAR_MOVIES

api_key = "395eb3021e5f1b9189388a23318b9cc6"

print("--- SERIES ---")
series_map = {}
for s in CURATED_POPULAR_SERIES:
    title = s["title"]
    r = httpx.get("https://api.themoviedb.org/3/search/tv", params={"api_key": api_key, "query": title})
    results = r.json().get("results", [])
    if results:
        top = results[0]
        series_map[title] = {
            "id": str(top["id"]),
            "poster": f"https://image.tmdb.org/t/p/w500{top.get('poster_path')}"
        }
        print(f"'{title}': ('{top['id']}', '{series_map[title]['poster']}'),")

print("\n--- MOVIES ---")
movie_map = {}
for m in CURATED_POPULAR_MOVIES:
    title = m["title"]
    r = httpx.get("https://api.themoviedb.org/3/search/movie", params={"api_key": api_key, "query": title})
    results = r.json().get("results", [])
    if results:
        top = results[0]
        movie_map[title] = {
            "id": str(top["id"]),
            "poster": f"https://image.tmdb.org/t/p/w500{top.get('poster_path')}"
        }
        print(f"'{title}': ('{top['id']}', '{movie_map[title]['poster']}'),")
