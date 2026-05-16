"""DataUpdateCoordinator for the Stash integration."""

from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_API_KEY, CONF_URL, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class StashDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    """Class to manage fetching Stash data."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name="Stash",
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )
        self._url = config_entry.data[CONF_URL]
        self._api_key = config_entry.data[CONF_API_KEY]

    async def _async_update_data(self) -> dict:
        """Fetch data from Stash API."""
        query = """
            query {
                stats {
                    sceneCount
                    performerCount
                    studioCount
                    movieCount
                    tagCount
                    galleryCount
                    imageCount
                    totalSize
                    totalDuration
                }
            }
        """

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
                    if response.status != 200:
                        raise UpdateFailed(
                            f"Error communicating with API: {response.status}"
                        )

                    result = await response.json()

                    if "errors" in result:
                        raise UpdateFailed(f"GraphQL errors: {result['errors']}")

                    if "data" not in result or "stats" not in result["data"]:
                        raise UpdateFailed("Invalid response from API")

                    return result["data"]["stats"]

        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
