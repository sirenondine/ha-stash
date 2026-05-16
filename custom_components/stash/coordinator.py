"""DataUpdateCoordinators for the Stash integration."""

from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_API_KEY, CONF_URL

_LOGGER = logging.getLogger(__name__)


class _StashCoordinatorBase(DataUpdateCoordinator[dict]):
    """Shared base for Stash coordinators."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        name: str,
        interval: int,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=name,
            update_interval=timedelta(seconds=interval),
        )
        self._url = config_entry.data[CONF_URL]
        self._api_key = config_entry.data[CONF_API_KEY]

    async def _post(self, query: str) -> dict:
        """POST a GraphQL query and return the data block."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self._url}/graphql",
                    headers={
                        "ApiKey": self._api_key,
                        "Content-Type": "application/json",
                    },
                    json={"query": query},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 401:
                        raise UpdateFailed("Authentication failed — check API key")
                    if response.status != 200:
                        text = await response.text()
                        _LOGGER.error("HTTP %d: %s", response.status, text)
                        raise UpdateFailed(
                            f"Error communicating with API: HTTP {response.status}"
                        )
                    result = await response.json()
                    if "errors" in result:
                        _LOGGER.error("GraphQL errors: %s", result["errors"])
                        raise UpdateFailed(f"GraphQL errors: {result['errors']}")
                    if "data" not in result:
                        raise UpdateFailed("Invalid response from API")
                    return result["data"]
        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.error("Error fetching data: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err


class StashStatsCoordinator(_StashCoordinatorBase):
    """Coordinator that polls library statistics (slow interval)."""

    def __init__(
        self, hass: HomeAssistant, config_entry: ConfigEntry, interval: int
    ) -> None:
        super().__init__(hass, config_entry, "Stash Stats", interval)

    async def _async_update_data(self) -> dict:
        """Fetch library stats. Returns the flat stats dict."""
        query = """
            query {
                stats {
                    scene_count
                    performer_count
                    studio_count
                    group_count
                    tag_count
                    gallery_count
                    image_count
                    scenes_size
                    images_size
                    scenes_duration
                    total_o_count
                    total_play_duration
                    total_play_count
                    scenes_played
                }
            }
        """
        data = await self._post(query)
        return data.get("stats", {})


class StashStatusCoordinator(_StashCoordinatorBase):
    """Coordinator that polls job queue, DLNA and version (fast interval)."""

    def __init__(
        self, hass: HomeAssistant, config_entry: ConfigEntry, interval: int
    ) -> None:
        super().__init__(hass, config_entry, "Stash Status", interval)

    async def _async_update_data(self) -> dict:
        """Fetch status data. Returns a structured dict."""
        query = """
            query {
                version {
                    version
                }
                latestversion {
                    version
                }
                jobQueue {
                    id
                    status
                    description
                    progress
                }
                dlnaStatus {
                    running
                }
            }
        """
        data = await self._post(query)
        return {
            "version": (data.get("version") or {}).get("version"),
            "latest_version": (data.get("latestversion") or {}).get("version"),
            "jobs": data.get("jobQueue") or [],
            "dlna_running": (data.get("dlnaStatus") or {}).get("running", False),
        }
