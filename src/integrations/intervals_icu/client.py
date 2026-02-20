import logging
from datetime import datetime
from typing import Any

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class IntervalsICUError(Exception):
    """Base exception for Intervals.icu API errors."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"Intervals.icu API error {status_code}: {message}")


class IntervalsICUClient:
    """Async client for Intervals.icu REST API.

    Uses Basic Auth with username='API_KEY' and password=<your_api_key>.
    Athlete ID '0' auto-resolves to the key owner.
    """

    def __init__(
        self,
        api_key: str | None = None,
        athlete_id: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.intervals_api_key
        self._athlete_id = athlete_id or settings.intervals_athlete_id
        self._base_url = base_url or settings.intervals_base_url
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "IntervalsICUClient":
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            auth=httpx.BasicAuth(username="API_KEY", password=self._api_key),
            timeout=httpx.Timeout(30.0),
            headers={"Accept": "application/json"},
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Client not initialized. Use 'async with IntervalsICUClient():'")
        return self._client

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        client = self._ensure_client()
        response = await client.request(method, path, **kwargs)
        if response.status_code >= 400:
            raise IntervalsICUError(response.status_code, response.text)
        result: Any = response.json()
        return result

    # ── Activities ──────────────────────────────────────────────

    async def get_activities(self, oldest: str, newest: str) -> list[dict[str, Any]]:
        """List completed activities in date range (YYYY-MM-DD)."""
        result: list[dict[str, Any]] = await self._request(
            "GET",
            f"/athlete/{self._athlete_id}/activities",
            params={"oldest": oldest, "newest": newest},
        )
        return result

    async def get_activity(self, activity_id: str, intervals: bool = True) -> dict[str, Any]:
        """Get single activity with optional interval data."""
        result: dict[str, Any] = await self._request(
            "GET",
            f"/activity/{activity_id}",
            params={"intervals": str(intervals).lower()},
        )
        return result

    # ── Events / Planned Workouts ───────────────────────────────

    async def get_events(self, oldest: str, newest: str) -> list[dict[str, Any]]:
        """List calendar events (planned workouts) in date range."""
        result: list[dict[str, Any]] = await self._request(
            "GET",
            f"/athlete/{self._athlete_id}/events",
            params={"oldest": oldest, "newest": newest},
        )
        return result

    # ── Wellness ────────────────────────────────────────────────

    async def get_wellness(self, oldest: str, newest: str) -> list[dict[str, Any]]:
        """List wellness records (weight, HR, HRV, sleep, etc.) in date range."""
        result: list[dict[str, Any]] = await self._request(
            "GET",
            f"/athlete/{self._athlete_id}/wellness",
            params={"oldest": oldest, "newest": newest},
        )
        return result

    async def get_wellness_today(self) -> dict[str, Any]:
        """Get today's wellness record."""
        today = datetime.now().strftime("%Y-%m-%d")
        result: dict[str, Any] = await self._request(
            "GET",
            f"/athlete/{self._athlete_id}/wellness/{today}",
        )
        return result

    # ── Athlete ─────────────────────────────────────────────────

    async def get_athlete(self) -> dict[str, Any]:
        """Get athlete profile (FTP, weight, zones, etc.)."""
        result: dict[str, Any] = await self._request(
            "GET",
            f"/athlete/{self._athlete_id}",
        )
        return result
