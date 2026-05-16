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

    async def async_query(self, query: str) -> dict:
        """Execute an ad-hoc GraphQL query and return the data block."""
        return await self._post(query)

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
        """Fetch library stats and last O'd scene. Returns a flat dict."""
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
                lastOScene: findScenes(
                    filter: { per_page: 1, sort: "o_counter", direction: DESC }
                    scene_filter: { o_counter: { value: 0, modifier: GREATER_THAN } }
                ) {
                    scenes {
                        id
                        title
                        date
                        o_counter
                        o_history
                    }
                }
                lastWatchedScene: findScenes(
                    filter: { per_page: 1, sort: "play_count", direction: DESC }
                    scene_filter: { play_count: { value: 0, modifier: GREATER_THAN } }
                ) {
                    scenes {
                        id
                        title
                        date
                        play_count
                        last_played_at
                    }
                }
                version {
                    version
                }
                latestversion {
                    version
                }
                scenesWithO: findScenes(
                    filter: { per_page: 5000, sort: "o_counter", direction: DESC }
                    scene_filter: { o_counter: { value: 0, modifier: GREATER_THAN } }
                ) {
                    scenes {
                        o_counter
                        performers { id name }
                    }
                }
            }
        """
        data = await self._post(query)
        result = dict(data.get("stats", {}))

        # Version info (polled slowly — latestversion calls GitHub API)
        result["version"] = (data.get("version") or {}).get("version")
        result["latest_version"] = (data.get("latestversion") or {}).get("version")

        # Merge last O'd scene data into the flat result dict
        o_scenes = (data.get("lastOScene") or {}).get("scenes", [])
        if o_scenes:
            scene = o_scenes[0]
            o_history = scene.get("o_history") or []
            result["last_o_scene_title"] = scene.get("title")
            result["last_o_scene_date"] = scene.get("date")
            result["last_o_scene_o_count"] = scene.get("o_counter")
            result["last_o_scene_last_o_at"] = o_history[-1] if o_history else None
        else:
            result["last_o_scene_title"] = None
            result["last_o_scene_date"] = None
            result["last_o_scene_o_count"] = None
            result["last_o_scene_last_o_at"] = None

        # Merge last watched scene data into the flat result dict
        watched_scenes = (data.get("lastWatchedScene") or {}).get("scenes", [])
        if watched_scenes:
            scene = watched_scenes[0]
            result["last_watched_scene_title"] = scene.get("title")
            result["last_watched_scene_date"] = scene.get("date")
            result["last_watched_scene_play_count"] = scene.get("play_count")
            result["last_watched_scene_last_played_at"] = scene.get("last_played_at")
        else:
            result["last_watched_scene_title"] = None
            result["last_watched_scene_date"] = None
            result["last_watched_scene_play_count"] = None
            result["last_watched_scene_last_played_at"] = None

        # Aggregate scene o_counter by performer to find true top performers.
        # performer.o_counter is a separate manual counter; summing scene o_counters
        # across each performer's scenes gives the correct activity-based ranking.
        performer_totals: dict[str, dict] = {}
        for scene in (data.get("scenesWithO") or {}).get("scenes", []):
            scene_o = scene.get("o_counter") or 0
            for performer in scene.get("performers") or []:
                pid = performer.get("id")
                if not pid:
                    continue
                if pid not in performer_totals:
                    performer_totals[pid] = {
                        "name": performer.get("name", ""),
                        "o_count": 0,
                    }
                performer_totals[pid]["o_count"] += scene_o

        sorted_performers = sorted(
            performer_totals.values(),
            key=lambda p: p["o_count"],
            reverse=True,
        )[:5]
        result["top_performers"] = [
            {
                "rank": i + 1,
                "name": p["name"],
                "o_count": p["o_count"],
            }
            for i, p in enumerate(sorted_performers)
        ]

        return result


class StashStatusCoordinator(_StashCoordinatorBase):
    """Coordinator that polls job queue, DLNA and version (fast interval)."""

    def __init__(
        self, hass: HomeAssistant, config_entry: ConfigEntry, interval: int
    ) -> None:
        super().__init__(hass, config_entry, "Stash Status", interval)

    async def _async_update_data(self) -> dict:
        """Fetch job queue and DLNA status. Returns a structured dict."""
        query = """
            query {
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
            "jobs": data.get("jobQueue") or [],
            "dlna_running": (data.get("dlnaStatus") or {}).get("running", False),
        }
