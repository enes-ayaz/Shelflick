import os
import sys
import asyncio
import httpx
from dotenv import load_dotenv

# Load from both current folder and backend folder
load_dotenv()
load_dotenv("backend/.env")

# Ensure clean UTF-8 console output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

api_key = os.getenv("TMDB_API_KEY")
read_token = os.getenv("TMDB_READ_ACCESS_TOKEN")

print(f"--> TMDB_API_KEY yüklendi mi?: {'EVET' if api_key else 'HAYIR'}")
print(f"--> TMDB_READ_ACCESS_TOKEN yüklendi mi?: {'EVET' if read_token else 'HAYIR'}")

import httpcore
from httpcore._backends.anyio import AnyIOBackend

class TMDBDoHBackend(AnyIOBackend):
    async def connect_tcp(self, host: str, port: int, *args, **kwargs):
        if host == "api.themoviedb.org":
            # CloudFront IP
            host = "13.227.173.110"
        return await super().connect_tcp(host, port, *args, **kwargs)

class TMDBDoHTransport(httpx.AsyncHTTPTransport):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pool = httpcore.AsyncConnectionPool(network_backend=TMDBDoHBackend())

async def test_call():
    url = "https://api.themoviedb.org/3/movie/popular"
    headers = {"Accept": "application/json"}
    params = {}
    
    if read_token:
        headers["Authorization"] = f"Bearer {read_token}"
    elif api_key:
        params["api_key"] = api_key

    try:
        transport = TMDBDoHTransport()
        async with httpx.AsyncClient(transport=transport, timeout=10.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            print(f"--> HTTP Durum Kodu: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"--> BAŞARILI! Gelen ilk film: {data['results'][0]['title']}")
            else:
                print(f"--> HATA YANITI: {resp.text}")
    except Exception as e:
        print(f"--> BAĞLANTI / SOKET HATASI: {type(e).__name__} - {e}")

asyncio.run(test_call())

