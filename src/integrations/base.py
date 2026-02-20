from abc import ABC, abstractmethod
from typing import Any


class BaseIntegration(ABC):
    """Abstract base class for external service integrations.

    All integrations (Intervals.icu, Veloplanner, etc.) should implement this.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the integration."""

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Whether this integration is configured and active."""

    @abstractmethod
    async def sync(self) -> None:
        """Synchronize data from the external service to local DB."""

    @abstractmethod
    async def get_activities(self, oldest: str, newest: str) -> list[dict[str, Any]]:
        """Fetch activities in date range (YYYY-MM-DD)."""

    @abstractmethod
    async def get_wellness(self, oldest: str, newest: str) -> list[dict[str, Any]]:
        """Fetch wellness data in date range (YYYY-MM-DD)."""
