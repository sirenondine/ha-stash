"""Media player platform for Stash — library browser."""

from __future__ import annotations

import logging

from homeassistant.components.media_player import (
    BrowseMedia,
    MediaClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_API_KEY, CONF_URL, DOMAIN
from .coordinator import StashStatsCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Stash media player."""
    coordinator: StashStatsCoordinator = entry.runtime_data.stats_coordinator
    async_add_entities([StashMediaPlayer(coordinator, entry)])


class StashMediaPlayer(CoordinatorEntity[StashStatsCoordinator], MediaPlayerEntity):
    """Media player entity that exposes the Stash library as a browseable tree."""

    _attr_has_entity_name = True
    _attr_name = "Library"
    _attr_icon = "mdi:filmstrip-box-multiple"
    _attr_supported_features = MediaPlayerEntityFeature.BROWSE_MEDIA
    _attr_media_content_type = MediaType.VIDEO

    def __init__(
        self,
        coordinator: StashStatsCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialise the media player."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_library"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Stash",
            manufacturer="Stash",
            entry_type=DeviceEntryType.SERVICE,
        )
        self._url = entry.data[CONF_URL]
        self._api_key = entry.data[CONF_API_KEY]

    # ------------------------------------------------------------------
    # State — this entity is a browser only, not a real player
    # ------------------------------------------------------------------

    @property
    def state(self) -> MediaPlayerState:
        """Always idle — this entity browses, it does not play."""
        return MediaPlayerState.IDLE

    # ------------------------------------------------------------------
    # Thumbnail helpers
    # ------------------------------------------------------------------

    def _scene_thumb(self, scene_id: str) -> str:
        return f"{self._url}/scene/{scene_id}/screenshot?apikey={self._api_key}"

    def _performer_thumb(self, performer_id: str) -> str:
        return f"{self._url}/performer/{performer_id}/image?apikey={self._api_key}"

    def _studio_thumb(self, studio_id: str) -> str:
        return f"{self._url}/studio/{studio_id}/image?apikey={self._api_key}"

    # ------------------------------------------------------------------
    # Scene helper — converts a raw scene dict to a BrowseMedia leaf
    # ------------------------------------------------------------------

    def _scene_item(self, scene: dict) -> BrowseMedia:
        scene_id = scene.get("id", "")
        title = scene.get("title") or f"Scene {scene_id}"
        date = scene.get("date", "")
        return BrowseMedia(
            title=f"{title} ({date})" if date else title,
            media_class=MediaClass.VIDEO,
            media_content_type=MediaType.VIDEO,
            media_content_id=f"scenes/{scene_id}",
            can_play=False,
            can_expand=False,
            thumbnail=self._scene_thumb(scene_id),
        )

    # ------------------------------------------------------------------
    # Browse entry point
    # ------------------------------------------------------------------

    async def async_browse_media(
        self,
        media_content_type: str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        """Return the browseable media tree for the requested node."""
        if not media_content_id or media_content_id == "library":
            return self._build_root()

        parts = media_content_id.split("/")
        section = parts[0]
        item_id = parts[1] if len(parts) > 1 else None

        if section == "scenes":
            return await self._browse_scenes()
        if section == "performers":
            return (
                await self._browse_performer_scenes(item_id)
                if item_id
                else await self._browse_performers()
            )
        if section == "studios":
            return (
                await self._browse_studio_scenes(item_id)
                if item_id
                else await self._browse_studios()
            )
        if section == "tags":
            return (
                await self._browse_tag_scenes(item_id)
                if item_id
                else await self._browse_tags()
            )

        return self._build_root()

    # ------------------------------------------------------------------
    # Root level — no API call needed
    # ------------------------------------------------------------------

    def _build_root(self) -> BrowseMedia:
        """Return the top-level library browser."""
        return BrowseMedia(
            title="Stash Library",
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            media_content_id="library",
            can_play=False,
            can_expand=True,
            children=[
                BrowseMedia(
                    title="Scenes",
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.VIDEO,
                    media_content_id="scenes",
                    can_play=False,
                    can_expand=True,
                ),
                BrowseMedia(
                    title="Performers",
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.VIDEO,
                    media_content_id="performers",
                    can_play=False,
                    can_expand=True,
                ),
                BrowseMedia(
                    title="Studios",
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.VIDEO,
                    media_content_id="studios",
                    can_play=False,
                    can_expand=True,
                ),
                BrowseMedia(
                    title="Tags",
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.VIDEO,
                    media_content_id="tags",
                    can_play=False,
                    can_expand=True,
                ),
            ],
        )

    # ------------------------------------------------------------------
    # Scenes
    # ------------------------------------------------------------------

    async def _browse_scenes(self) -> BrowseMedia:
        """Return the 48 most recently dated scenes."""
        data = await self.coordinator.async_query("""
            query {
                findScenes(filter: { per_page: 48, sort: "date", direction: DESC }) {
                    scenes { id title date }
                }
            }
        """)
        scenes = (data.get("findScenes") or {}).get("scenes", [])
        return BrowseMedia(
            title="Scenes",
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            media_content_id="scenes",
            can_play=False,
            can_expand=True,
            children=[self._scene_item(s) for s in scenes],
        )

    # ------------------------------------------------------------------
    # Performers
    # ------------------------------------------------------------------

    async def _browse_performers(self) -> BrowseMedia:
        """Return all performers sorted alphabetically."""
        data = await self.coordinator.async_query("""
            query {
                findPerformers(filter: { per_page: 250, sort: "name", direction: ASC }) {
                    performers { id name scene_count }
                }
            }
        """)
        performers = (data.get("findPerformers") or {}).get("performers", [])
        children = [
            BrowseMedia(
                title=f"{p.get('name')} ({p.get('scene_count', 0)} scenes)",
                media_class=MediaClass.ARTIST,
                media_content_type=MediaType.VIDEO,
                media_content_id=f"performers/{p.get('id')}",
                can_play=False,
                can_expand=True,
                thumbnail=self._performer_thumb(p.get("id", "")),
            )
            for p in performers
        ]
        return BrowseMedia(
            title="Performers",
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            media_content_id="performers",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _browse_performer_scenes(self, performer_id: str) -> BrowseMedia:
        """Return scenes for a specific performer."""
        query = f"""
            query {{
                findScenes(
                    filter: {{ per_page: 48, sort: "date", direction: DESC }}
                    scene_filter: {{
                        performers: {{ modifier: INCLUDES, value: ["{performer_id}"] }}
                    }}
                ) {{
                    scenes {{ id title date }}
                }}
                findPerformer(id: "{performer_id}") {{ name }}
            }}
        """
        data = await self.coordinator.async_query(query)
        scenes = (data.get("findScenes") or {}).get("scenes", [])
        name = (data.get("findPerformer") or {}).get("name", "Performer")
        return BrowseMedia(
            title=name,
            media_class=MediaClass.ARTIST,
            media_content_type=MediaType.VIDEO,
            media_content_id=f"performers/{performer_id}",
            can_play=False,
            can_expand=True,
            thumbnail=self._performer_thumb(performer_id),
            children=[self._scene_item(s) for s in scenes],
        )

    # ------------------------------------------------------------------
    # Studios
    # ------------------------------------------------------------------

    async def _browse_studios(self) -> BrowseMedia:
        """Return all studios sorted alphabetically."""
        data = await self.coordinator.async_query("""
            query {
                findStudios(filter: { per_page: 250, sort: "name", direction: ASC }) {
                    studios { id name scene_count }
                }
            }
        """)
        studios = (data.get("findStudios") or {}).get("studios", [])
        children = [
            BrowseMedia(
                title=f"{s.get('name')} ({s.get('scene_count', 0)} scenes)",
                media_class=MediaClass.DIRECTORY,
                media_content_type=MediaType.VIDEO,
                media_content_id=f"studios/{s.get('id')}",
                can_play=False,
                can_expand=True,
                thumbnail=self._studio_thumb(s.get("id", "")),
            )
            for s in studios
        ]
        return BrowseMedia(
            title="Studios",
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            media_content_id="studios",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _browse_studio_scenes(self, studio_id: str) -> BrowseMedia:
        """Return scenes for a specific studio."""
        query = f"""
            query {{
                findScenes(
                    filter: {{ per_page: 48, sort: "date", direction: DESC }}
                    scene_filter: {{
                        studios: {{ modifier: INCLUDES, value: ["{studio_id}"], depth: 0 }}
                    }}
                ) {{
                    scenes {{ id title date }}
                }}
                findStudio(id: "{studio_id}") {{ name }}
            }}
        """
        data = await self.coordinator.async_query(query)
        scenes = (data.get("findScenes") or {}).get("scenes", [])
        name = (data.get("findStudio") or {}).get("name", "Studio")
        return BrowseMedia(
            title=name,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            media_content_id=f"studios/{studio_id}",
            can_play=False,
            can_expand=True,
            thumbnail=self._studio_thumb(studio_id),
            children=[self._scene_item(s) for s in scenes],
        )

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------

    async def _browse_tags(self) -> BrowseMedia:
        """Return all tags that have at least one scene, sorted alphabetically."""
        data = await self.coordinator.async_query("""
            query {
                findTags(filter: { per_page: 250, sort: "name", direction: ASC }) {
                    tags { id name scene_count }
                }
            }
        """)
        tags = (data.get("findTags") or {}).get("tags", [])
        children = [
            BrowseMedia(
                title=f"{t.get('name')} ({t.get('scene_count', 0)})",
                media_class=MediaClass.GENRE,
                media_content_type=MediaType.VIDEO,
                media_content_id=f"tags/{t.get('id')}",
                can_play=False,
                can_expand=True,
            )
            for t in tags
            if (t.get("scene_count") or 0) > 0
        ]
        return BrowseMedia(
            title="Tags",
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            media_content_id="tags",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _browse_tag_scenes(self, tag_id: str) -> BrowseMedia:
        """Return scenes for a specific tag."""
        query = f"""
            query {{
                findScenes(
                    filter: {{ per_page: 48, sort: "date", direction: DESC }}
                    scene_filter: {{
                        tags: {{ modifier: INCLUDES, value: ["{tag_id}"], depth: 0 }}
                    }}
                ) {{
                    scenes {{ id title date }}
                }}
                findTag(id: "{tag_id}") {{ name }}
            }}
        """
        data = await self.coordinator.async_query(query)
        scenes = (data.get("findScenes") or {}).get("scenes", [])
        name = (data.get("findTag") or {}).get("name", "Tag")
        return BrowseMedia(
            title=name,
            media_class=MediaClass.GENRE,
            media_content_type=MediaType.VIDEO,
            media_content_id=f"tags/{tag_id}",
            can_play=False,
            can_expand=True,
            children=[self._scene_item(s) for s in scenes],
        )
