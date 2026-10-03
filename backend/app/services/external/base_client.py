import logging
from typing import Any, Dict, Optional
import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseAsyncClient:
    """Reusable asynchronous HTTP client with pooling, timeout, and tenacity retries."""

    def __init__(
        self,
        base_url: str = "",
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._custom_headers = headers or {}
        self.timeout = timeout or settings.HTTP_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.HTTP_MAX_RETRIES
        self.transport = transport
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        """Returns or initializes an active httpx.AsyncClient instance."""
        if self._client is None or self._client.is_closed:
            default_headers = {
                "User-Agent": "MediaPulse/1.0 (+https://mediapulse.local)",
                "Accept": "application/json",
            }
            default_headers.update(self._custom_headers)
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=default_headers,
                timeout=httpx.Timeout(self.timeout, connect=5.0),
                follow_redirects=True,
                transport=self.transport,
            )
        return self._client


    async def close(self) -> None:
        """Closes the underlying HTTP client session."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "BaseAsyncClient":
        await self.get_client()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    @retry(
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.5, min=0.3, max=1.0),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Executes an HTTP request with automatic retry on transient network failures."""
        client = await self.get_client()
        url = endpoint if endpoint.startswith("http") else f"{self.base_url}/{endpoint.lstrip('/')}"
        
        response = await client.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            headers=headers,
        )
        response.raise_for_status()
        return response

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Convenience method for sending GET requests and parsing JSON response."""
        res = await self.request("GET", endpoint, params=params, headers=headers)
        return res.json()

    async def post(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Convenience method for sending POST requests and parsing JSON response."""
        res = await self.request("POST", endpoint, json_data=json_data, headers=headers)
        return res.json()
