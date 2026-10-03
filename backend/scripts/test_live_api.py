import httpx
import json

BASE_URL = "http://127.0.0.1:8000"


def test_cors_and_endpoints():
    print("=" * 60)
    print("FASTAPI LIVE ENDPOINTS & CORS VERIFICATION")
    print("=" * 60)

    # 1. Test CORS Preflight
    print("\n[1] Testing CORS Preflight (OPTIONS /api/v1/recommend)...")
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    with httpx.Client() as client:
        resp = client.options(f"{BASE_URL}/api/v1/recommend", headers=headers)
        print(f"Status Code: {resp.status_code}")
        print("CORS Headers:")
        for k in ["access-control-allow-origin", "access-control-allow-credentials", "access-control-allow-methods"]:
            print(f"  {k}: {resp.headers.get(k)}")
        assert resp.status_code == 200, "CORS preflight failed!"
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000", "Wrong allow-origin header"
        assert resp.headers.get("access-control-allow-credentials") == "true", "Credentials not allowed"
        print("-> CORS Preflight PASSED!")

        # 2. Test Recommendation Post
        print("\n[2] Testing POST /api/v1/recommend with natural language query...")
        req_headers = {"Origin": "http://localhost:3000", "Content-Type": "application/json"}
        req_payload = {
            "prompt": "karanlık psikolojik gerilim",
            "limit": 5,
        }
        post_resp = client.post(f"{BASE_URL}/api/v1/recommend", headers=req_headers, json=req_payload, timeout=20.0)
        print(f"Status Code: {post_resp.status_code}")
        assert post_resp.status_code == 200, f"Recommendation failed: {post_resp.text}"
        data = post_resp.json()
        print("Response received successfully:")
        print(f"  Media Title       : {data['recommended_media']['title']}")
        print(f"  Media Source      : {data['recommended_media']['source']}")
        print(f"  Base Score        : {data['recommended_media']['base_score']}")
        print(f"  Justification     : {data['justification']}")
        print(f"  Parsed Intent     : {data['parsed_intent']}")
        print("-> POST /api/v1/recommend PASSED!")

        # 3. Test Random Discovery Endpoint
        print("\n[3] Testing GET /api/v1/recommend/random ('Şansıma Güveniyorum')...")
        rand_resp = client.get(f"{BASE_URL}/api/v1/recommend/random", headers={"Origin": "http://localhost:3000"}, timeout=20.0)
        print(f"Status Code: {rand_resp.status_code}")
        assert rand_resp.status_code == 200, f"Random discovery failed: {rand_resp.text}"
        rand_data = rand_resp.json()
        print(f"  Random Pick       : {rand_data['recommended_media']['title']}")
        print(f"  Score             : {rand_data['recommended_media']['base_score']}")
        print(f"  Justification     : {rand_data['justification']}")
        print("-> GET /api/v1/recommend/random PASSED!")

    print("\n" + "=" * 60)
    print("ALL API ENDPOINTS & CORS TESTS PASSED 100%!")
    print("=" * 60)


if __name__ == "__main__":
    test_cors_and_endpoints()
