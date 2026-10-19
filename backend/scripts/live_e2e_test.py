import sys
import time
import uuid
import httpx

# Ensure console supports utf-8 output without crash
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND_URL = "https://shelflick-api.onrender.com"
FRONTEND_URL = "https://www.shelflick.com"

def log_test(name: str, passed: bool, detail: str = ""):
    status = " PASS " if passed else " FAIL "
    color_start = "\033[92m" if passed else "\033[91m"
    color_end = "\033[0m"
    print(f"[{color_start}{status}{color_end}] {name}")
    if detail:
        for line in detail.strip().split("\n"):
            print(f"       {line}")

def run_all_tests():
    print("=" * 70)
    print("SHELFLICK FULL PRODUCTION LIVE END-TO-END TEST SUITE")
    print(f"Backend  : {BACKEND_URL}")
    print(f"Frontend : {FRONTEND_URL}")
    print("=" * 70)

    client = httpx.Client(timeout=35.0)
    all_passed = True

    # 1. Health & Database Connectivity
    print("\n--- 1. Health & System Connectivity ---")
    try:
        resp = client.get(f"{BACKEND_URL}/health")
        data = resp.json()
        passed = (resp.status_code == 200 and data.get("status") == "healthy" and data.get("database") == "connected")
        log_test("GET /health (Database & Service status)", passed, f"Status: {resp.status_code}, DB: {data.get('database')}")
        if not passed: all_passed = False
    except Exception as e:
        log_test("GET /health", False, str(e))
        all_passed = False

    # 2. Curated & Search Poster Source (Band of Brothers check)
    print("\n--- 2. Poster Source Verification (Band of Brothers) ---")
    try:
        resp = client.get(f"{BACKEND_URL}/api/v1/search/live", params={"q": "Band of Brothers"})
        items = resp.json()
        passed = False
        detail = []
        for it in items:
            p = it.get("poster_path") or ""
            detail.append(f"{it.get('title')} ({it.get('type')}) -> {p[:65]}...")
            if "band of brothers" in (it.get("title") or "").lower() or "kardeşler" in (it.get("title") or "").lower():
                if "static.tvmaze.com" not in p and "image.tmdb.org" in p:
                    passed = True
        log_test("Band of Brothers has official TMDB artwork (No TVMaze headshots)", passed, "\n".join(detail[:3]))
        if not passed: all_passed = False
    except Exception as e:
        log_test("Band of Brothers poster check", False, str(e))
        all_passed = False

    # 3. Anime Isolation in Live Search
    print("\n--- 3. Anime Isolation in Live Search ---")
    try:
        # 3a: General search for 'savaş' (NO filter) -> must NOT contain any ANILIST
        resp = client.get(f"{BACKEND_URL}/api/v1/search/live", params={"q": "savaş"})
        items = resp.json()
        anime_items = [it for it in items if it.get("source") == "ANILIST" or it.get("type") == "ANIME"]
        passed_3a = (len(anime_items) == 0 and len(items) > 0)
        detail_3a = f"Total results: {len(items)}, Anime found: {len(anime_items)}"
        log_test("General search 'savaş' (ALL filter) has ZERO anime", passed_3a, detail_3a)
        if not passed_3a: all_passed = False

        # 3b: General search for 'tarih' (NO filter) -> must NOT contain any ANILIST
        resp = client.get(f"{BACKEND_URL}/api/v1/search/live", params={"q": "tarih"})
        items = resp.json()
        anime_items = [it for it in items if it.get("source") == "ANILIST" or it.get("type") == "ANIME"]
        passed_3b = (len(anime_items) == 0 and len(items) > 0)
        detail_3b = f"Total results: {len(items)}, Anime found: {len(anime_items)}"
        log_test("General search 'tarih' (ALL filter) has ZERO anime", passed_3b, detail_3b)
        if not passed_3b: all_passed = False

        # 3c: Anime filter explicitly selected: 'savaş' + type=ANIME
        resp = client.get(f"{BACKEND_URL}/api/v1/search/live", params={"q": "savaş", "type": "ANIME"})
        items = resp.json()
        passed_3c = (len(items) > 0 and all(it.get("source") == "ANILIST" or it.get("type") == "ANIME" for it in items))
        detail_3c = f"Found {len(items)} items, e.g. {items[0].get('title') if items else 'None'}"
        log_test("Explicit filter 'type=ANIME' returns ONLY anime", passed_3c, detail_3c)
        if not passed_3c: all_passed = False

        # 3d: Explicit known anime title: 'Attack on Titan'
        resp = client.get(f"{BACKEND_URL}/api/v1/search/live", params={"q": "Attack on Titan"})
        items = resp.json()
        has_anime = any(it.get("source") == "ANILIST" or it.get("type") == "ANIME" for it in items)
        log_test("Anime title 'Attack on Titan' without filter correctly includes anime", has_anime, f"Results: {len(items)}")
        if not has_anime: all_passed = False
    except Exception as e:
        log_test("Anime isolation live search", False, str(e))
        all_passed = False

    # 4. Recommendation Engine (Semantic Search & Intent Filtering)
    print("\n--- 4. Recommendation Engine (LLM + Candidate Filtering) ---")
    try:
        # 4a: 'en iyi savaş filmleri' (ALL filter)
        payload = {"prompt": "en iyi savaş filmleri", "limit": 5}
        resp = client.post(f"{BACKEND_URL}/api/v1/recommend", json=payload, timeout=45.0)
        data = resp.json()
        rec = data.get("recommended_media") or {}
        cand = data.get("candidates") or []
        is_anime = (rec.get("source") == "ANILIST") or any(c.get("source") == "ANILIST" for c in cand)
        poster = rec.get("poster_url") or rec.get("poster_path") or ""
        has_tmdb_poster = poster.startswith("https://image.tmdb.org")
        passed_4a = (resp.status_code == 200 and rec.get("title") and not is_anime and has_tmdb_poster)
        detail_4a = f"Pick: {rec.get('title')} ({rec.get('source')}, Score: {rec.get('base_score')})\nPoster: {poster}\nCandidates: {[c.get('title') for c in cand[:3]]}"
        log_test("Recommendation for 'savaş' returns War Masterwork, NO Anime, TMDB poster", passed_4a, detail_4a)
        if not passed_4a: all_passed = False

        # 4b: '[ANIME] karanlık anime öner' (ANIME filter)
        payload = {"prompt": "[ANIME] karanlık anime öner", "limit": 5}
        resp = client.post(f"{BACKEND_URL}/api/v1/recommend", json=payload, timeout=45.0)
        data = resp.json()
        rec = data.get("recommended_media") or {}
        passed_4b = (resp.status_code == 200 and rec.get("source") == "ANILIST")
        detail_4b = f"Pick: {rec.get('title')} ({rec.get('source')}, Score: {rec.get('base_score')})"
        log_test("Recommendation for '[ANIME]' returns AniList anime", passed_4b, detail_4b)
        if not passed_4b: all_passed = False
    except Exception as e:
        log_test("Recommendation engine", False, str(e))
        all_passed = False

    # 5. Random Discovery ('Şansıma Güveniyorum')
    print("\n--- 5. Random Discovery Endpoint ---")
    try:
        resp = client.get(f"{BACKEND_URL}/api/v1/recommend/random", timeout=25.0)
        data = resp.json()
        rec = data.get("recommended_media") or {}
        passed_5 = (resp.status_code == 200 and bool(rec.get("title")) and rec.get("source") != "ANILIST")
        detail_5 = f"Random Masterpiece: {rec.get('title')} ({rec.get('source')}, Score: {rec.get('base_score')})"
        log_test("GET /api/v1/recommend/random returns verified movie/series masterpiece (NO Anime)", passed_5, detail_5)
        if not passed_5: all_passed = False
    except Exception as e:
        log_test("Random discovery", False, str(e))
        all_passed = False

    # 6. Library Operations (Shelf / Database E2E)
    print("\n--- 6. Library & Shelf Management ---")
    try:
        # 6a: Get Library Stats
        resp = client.get(f"{BACKEND_URL}/api/v1/library/stats")
        data = resp.json()
        passed_6a = (resp.status_code == 200 and "total_watch_time_minutes" in data)
        log_test("GET /api/v1/library/stats returns user stats", passed_6a, f"Stats: {data}")
        if not passed_6a: all_passed = False

        # 6b: Add test item to library
        test_ext_id = str(999998)
        add_payload = {
            "media": {
                "external_id": test_ext_id,
                "title": "Automated Live Test Media",
                "source": "TMDB_MOVIE",
                "base_score": 8.5,
                "poster_url": "https://image.tmdb.org/t/p/w500/test.jpg",
                "release_year": 2024,
                "genres": ["Action", "Drama"],
                "synopsis": "Live test payload synopsis in Turkish."
            },
            "status": "PLAN_TO_WATCH"
        }
        resp = client.post(f"{BACKEND_URL}/api/v1/library/items", json=add_payload)
        passed_6b = resp.status_code in (200, 201)
        item_id = resp.json().get("id") if passed_6b else None
        log_test("POST /api/v1/library/items (Add to shelf)", passed_6b, f"Status: {resp.status_code}, UserMedia ID: {item_id}")
        if not passed_6b: all_passed = False

        # 6c: Delete test item to keep clean
        if item_id:
            del_resp = client.delete(f"{BACKEND_URL}/api/v1/library/items/{item_id}")
            passed_6c = del_resp.status_code in (200, 204)
            log_test("DELETE /api/v1/library/items/{id} (Clean up)", passed_6c, f"Status: {del_resp.status_code}")
            if not passed_6c: all_passed = False
    except Exception as e:
        log_test("Library operations", False, str(e))
        all_passed = False

    # 7. Frontend Reachability
    print("\n--- 7. Frontend Production Reachability ---")
    try:
        f_resp = client.get(FRONTEND_URL, follow_redirects=True, timeout=25.0)
        passed_7 = (f_resp.status_code == 200 and "shelflick" in f_resp.text.lower())
        log_test("Production Frontend (https://www.shelflick.com) 200 OK", passed_7, f"Status: {f_resp.status_code}, Length: {len(f_resp.text)}")
        if not passed_7: all_passed = False
    except Exception as e:
        log_test("Frontend reachability", False, str(e))
        all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("\033[92mALL PRODUCTION E2E LIVE TESTS PASSED SUCCESSFULLY (100%)!\033[0m")
    else:
        print("\033[91mSOME TESTS FAILED OR WAITING FOR DEPLOYMENT TO FINISH ROLLOUT.\033[0m")
    print("=" * 70)
    return all_passed

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
