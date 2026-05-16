"""Media player platform for Stash — library browser."""

from __future__ import annotations

import logging
from urllib.parse import quote

import aiohttp
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
    _attr_supported_features = (
        MediaPlayerEntityFeature.BROWSE_MEDIA
        | MediaPlayerEntityFeature.PLAY_MEDIA
        | MediaPlayerEntityFeature.STOP
    )
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
        # Currently displayed image/gallery (None = idle)
        self._current_media: dict | None = None

    # ------------------------------------------------------------------
    # State — idle normally, playing when showing an image/gallery
    # ------------------------------------------------------------------

    @property
    def state(self) -> MediaPlayerState:
        return (
            MediaPlayerState.PLAYING if self._current_media else MediaPlayerState.IDLE
        )

    @property
    def media_title(self) -> str | None:
        return self._current_media.get("title") if self._current_media else None

    @property
    def media_content_type(self) -> str:
        if self._current_media:
            return MediaType.IMAGE
        return MediaType.VIDEO

    @property
    def media_image_url(self) -> str | None:
        """Return a direct Stash URL for the current image (local network)."""
        if not self._current_media:
            return None
        kind = self._current_media.get("kind")
        item_id = self._current_media.get("id")
        if kind == "image":
            return f"{self._url}/image/{item_id}/image?apikey={self._api_key}"
        if kind == "gallery":
            return f"{self._url}/gallery/{item_id}/cover?apikey={self._api_key}"
        return None

    @property
    def media_image_remotely_accessible(self) -> bool:
        """Image URL points to local Stash — not reachable from outside the LAN."""
        return False

    async def async_media_stop(self) -> None:
        """Clear the currently displayed image and return to idle."""
        self._current_media = None
        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Play media — fires a HA event so automations can open Stash
    # ------------------------------------------------------------------

    async def async_play_media(
        self,
        media_type: str,
        media_id: str,
        **kwargs,
    ) -> None:
        """Display images/galleries inline; open everything else in Stash."""
        parts = media_id.split("/")
        section = parts[0]
        item_id = parts[1] if len(parts) > 1 else None

        if not item_id:
            _LOGGER.warning("Cannot handle media_id: %s", media_id)
            return

        # --- Images and galleries: show inline in the media player card ---
        if section in ("images", "galleries"):
            # Fetch the title so the media card shows something meaningful
            kind = section.rstrip("s")  # "image" or "gallery"
            try:
                data = await self.coordinator.async_query(
                    f'query {{ find{kind.title()}(id: "{item_id}") {{ title }} }}'
                )
                title = (data.get(f"find{kind.title()}") or {}).get(
                    "title"
                ) or f"{kind.title()} {item_id}"
            except Exception:  # pylint: disable=broad-except
                title = f"{kind.title()} {item_id}"

            self._current_media = {"kind": kind, "id": item_id, "title": title}
            self.async_write_ha_state()
            return

        # --- Everything else: open in Stash ---
        section_map = {
            "scenes": ("scenes", "scene"),
            "performers": ("performers", "performer"),
            "studios": ("studios", "studio"),
            "tags": ("tags", "tag"),
        }

        if section not in section_map:
            _LOGGER.warning("Cannot open Stash URL for media_id: %s", media_id)
            return

        url_path, type_label = section_map[section]
        stash_url = f"{self._url}/{url_path}/{item_id}"

        self.hass.bus.async_fire(
            "stash_open",
            {"url": stash_url, "type": type_label, "id": item_id},
        )
        _LOGGER.debug("Fired stash_open event: %s", stash_url)

        # If browser_mod is installed, show the page in a popup directly.
        # Otherwise fall back to a persistent notification with a clickable link.
        if self.hass.services.has_service("browser_mod", "popup"):
            await self.hass.services.async_call(
                "browser_mod",
                "popup",
                {
                    "title": f"Stash — {type_label.title()}",
                    "content": {"type": "webpage", "url": stash_url},
                    "size": "wide",
                },
            )
        else:
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "Open in Stash",
                    "message": (
                        f"[Open {type_label}]({stash_url})\n\n"
                        "_Tip: install [browser\_mod](https://github.com/thomasloven/hass-browser_mod)"
                        " for direct in-dashboard opening._"
                    ),
                    "notification_id": "stash_open",
                },
            )

    # ------------------------------------------------------------------
    # Thumbnail helpers
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Thumbnail proxy — routes through HA so remote access works
    # ------------------------------------------------------------------

    def _thumb(self, media_content_id: str) -> str:
        """Return an HA-proxied thumbnail URL that works locally and remotely."""
        encoded = quote(media_content_id, safe="")
        return (
            f"/api/media_player_proxy/{self.entity_id}"
            f"/browse_media/{MediaType.VIDEO}/{encoded}"
        )

    async def async_get_browse_image(
        self,
        media_content_type: str,
        media_content_id: str,
        media_image_id: str | None = None,
    ) -> tuple[bytes | None, str | None]:
        """Fetch the thumbnail from Stash and return it through HA's proxy."""
        parts = media_content_id.split("/")
        section = parts[0]
        item_id = parts[1] if len(parts) > 1 else None

        if not item_id:
            return None, None

        stash_thumb_map = {
            "scenes": f"{self._url}/scene/{item_id}/screenshot",
            "performers": f"{self._url}/performer/{item_id}/image",
            "studios": f"{self._url}/studio/{item_id}/image",
            "galleries": f"{self._url}/gallery/{item_id}/cover",
            "images": f"{self._url}/image/{item_id}/thumbnail",
        }
        stash_url = stash_thumb_map.get(section)
        if not stash_url:
            return None, None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{stash_url}?apikey={self._api_key}",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        return None, None
                    return await resp.read(), resp.content_type
        except Exception:  # pylint: disable=broad-except
            return None, None

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
            can_play=True,
            can_expand=False,
            thumbnail=self._thumb(f"scenes/{scene_id}"),
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
        if section == "galleries":
            return (
                await self._browse_gallery_images(item_id)
                if item_id
                else await self._browse_galleries()
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
                BrowseMedia(
                    title="Galleries",
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.IMAGE,
                    media_content_id="galleries",
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
                can_play=True,
                can_expand=True,
                thumbnail=self._thumb(f"performers/{p.get('id')}"),
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
            thumbnail=self._thumb(f"performers/{performer_id}"),
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
                can_play=True,
                can_expand=True,
                thumbnail=self._thumb(f"studios/{s.get('id')}"),
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
            thumbnail=self._thumb(f"studios/{studio_id}"),
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

    # ------------------------------------------------------------------
    # Galleries
    # ------------------------------------------------------------------

    async def _browse_galleries(self) -> BrowseMedia:
        """Return all galleries sorted by date."""
        data = await self.coordinator.async_query("""
            query {
                findGalleries(filter: { per_page: 100, sort: "date", direction: DESC }) {
                    galleries { id title date image_count }
                }
            }
        """)
        galleries = (data.get("findGalleries") or {}).get("galleries", [])
        children = [
            BrowseMedia(
                title=(
                    f"{g.get('title') or 'Gallery'}"
                    f" ({g.get('image_count', 0)} images)"
                    + (f" — {g.get('date')}" if g.get("date") else "")
                ),
                media_class=MediaClass.ALBUM,
                media_content_type=MediaType.IMAGE,
                media_content_id=f"galleries/{g.get('id')}",
                can_play=True,
                can_expand=True,
                thumbnail=self._thumb(f"galleries/{g.get('id')}"),
            )
            for g in galleries
        ]
        return BrowseMedia(
            title="Galleries",
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.IMAGE,
            media_content_id="galleries",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _browse_gallery_images(self, gallery_id: str) -> BrowseMedia:
        """Return images within a specific gallery."""
        query = f"""
            query {{
                findImages(
                    filter: {{ per_page: 100 }}
                    image_filter: {{
                        galleries: {{ modifier: INCLUDES, value: ["{gallery_id}"] }}
                    }}
                ) {{
                    images {{ id title }}
                }}
                findGallery(id: "{gallery_id}") {{ title }}
            }}
        """
        data = await self.coordinator.async_query(query)
        images = (data.get("findImages") or {}).get("images", [])
        title = (data.get("findGallery") or {}).get("title") or "Gallery"
        children = [
            BrowseMedia(
                title=img.get("title") or f"Image {img.get('id')}",
                media_class=MediaClass.IMAGE,
                media_content_type=MediaType.IMAGE,
                media_content_id=f"images/{img.get('id')}",
                can_play=True,
                can_expand=False,
                thumbnail=self._thumb(f"images/{img.get('id')}"),
            )
            for img in images
        ]
        return BrowseMedia(
            title=title,
            media_class=MediaClass.ALBUM,
            media_content_type=MediaType.IMAGE,
            media_content_id=f"galleries/{gallery_id}",
            can_play=True,
            can_expand=True,
            thumbnail=self._thumb(f"galleries/{gallery_id}"),
            children=children,
        )
