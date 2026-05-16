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

        try:
            async with aiohttp.ClientSession() as session:
                _LOGGER.debug("Fetching data from %s/graphql", self._url)

                async with session.post(
                    f"{self._url}/graphql",
                    headers={
                        "ApiKey": self._api_key,
                        "Content-Type": "application/json",
                    },
                    json={"query": query},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    _LOGGER.debug("Response status: %d", response.status)

                    if response.status == 401:
                        raise UpdateFailed("Authentication failed - check API key")

                    if response.status != 200:
                        error_text = await response.text()
                        _LOGGER.error("HTTP %d: %s", response.status, error_text)
                        raise UpdateFailed(
                            f"Error communicating with API: HTTP {response.status}"
                        )

                    result = await response.json()
                    _LOGGER.debug("Response data: %s", result)

                    if "errors" in result:
                        _LOGGER.error("GraphQL errors: %s", result["errors"])
                        raise UpdateFailed(f"GraphQL errors: {result['errors']}")

                    if "data" not in result or "stats" not in result["data"]:
                        raise UpdateFailed("Invalid response from API")

                    return result["data"]["stats"]

        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.error("Error fetching data: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err
