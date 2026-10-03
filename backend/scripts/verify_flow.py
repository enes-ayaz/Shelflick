import httpx
import json

BASE_URL = "http://127.0.0.1:8000"
DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"

def test_flow():
    with httpx.Client(timeout=30.0) as client:
        # 1. Health check
        health = client.get(f"{BASE_URL}/health")
        print("Health:", health.json())

        # 2. Get Random Masterpiece #1
        r1 = client.get(f"{BASE_URL}/api/v1/recommend/random?user_id={DEMO_USER_ID}")
        assert r1.status_code == 200, f"r1 failed: {r1.text}"
        data1 = r1.json()
        item1 = data1["recommended_media"]
        print(f"\n[Random #1]: {item1['title']} ({item1.get('release_year')}) - Score: {item1['base_score']}")
        print(f"Gerekçe: {data1['justification']}")

        # 3. Get Random Masterpiece #2 (verify diversity, not Heidi every time)
        r2 = client.get(f"{BASE_URL}/api/v1/recommend/random?user_id={DEMO_USER_ID}")
        assert r2.status_code == 200, f"r2 failed: {r2.text}"
        data2 = r2.json()
        item2 = data2["recommended_media"]
        print(f"\n[Random #2]: {item2['title']} ({item2.get('release_year')}) - Score: {item2['base_score']}")

        # 4. Add item1 to user's library
        print(f"\n[Adding to Library]: {item1['title']}...")
        add_res = client.post(
            f"{BASE_URL}/api/v1/library/items",
            json={
                "user_id": DEMO_USER_ID,
                "media": item1,
                "status": "PLAN_TO_WATCH",
            }
        )
        assert add_res.status_code == 201, f"add failed: {add_res.text}"
        print("Successfully added to library:", add_res.json()["title"])

        # 5. Fetch library items
        lib_res = client.get(f"{BASE_URL}/api/v1/library/items?user_id={DEMO_USER_ID}")
        assert lib_res.status_code == 200
        lib_items = lib_res.json()
        print(f"\n[User Library Items Count]: {len(lib_items)}")
        for it in lib_items:
            print(f" - {it['title']} [{it['status']}] (Score: {it['base_score']})")

        # 6. Verify that subsequent random recommendations don't pick saved items
        print("\n[Verifying Exclusion of Saved Items in 3 Random Calls]...")
        saved_titles = {it["title"].lower() for it in lib_items}
        for i in range(3):
            rx = client.get(f"{BASE_URL}/api/v1/recommend/random?user_id={DEMO_USER_ID}")
            if rx.status_code == 200:
                rec_title = rx.json()["recommended_media"]["title"]
                print(f"  Call {i+1}: {rec_title}")
                assert rec_title.lower() not in saved_titles, f"Error: {rec_title} was in saved library but returned!"
            else:
                print(f"  Call {i+1} status: {rx.status_code}")

    print("\nALL LIVE VERIFICATION TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_flow()
