"""Media source platform for Stash — galleries and images in the global browser."""

from __future__ import annotations

import logging

import aiohttp
from homeassistant.components.media_player import MediaClass, MediaType
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceError,
    MediaSourceItem,
    PlayMedia,
)
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, CONF_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_get_media_source(hass: HomeAssistant) -> StashMediaSource:
    """Return the Stash media source — called automatically by HA."""
    return StashMediaSource(hass)


class StashMediaSource(MediaSource):
    """Expose Stash galleries and images in HA's global media browser."""

    name = "Stash"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialise."""
        super().__init__(DOMAIN)
        self.hass = hass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _config(self) -> tuple[str, str]:
        """Return (url, api_key) from the first active config entry."""
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            return entry.data[CONF_URL], entry.data[CONF_API_KEY]
        raise MediaSourceError("No active Stash config entry found")

    async def _query(self, query: str) -> dict:
        """Execute a GraphQL query against Stash."""
        url, api_key = self._config()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{url}/graphql",
                    headers={"ApiKey": api_key, "Content-Type": "application/json"},
                    json={"query": query},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        raise MediaSourceError(f"HTTP {resp.status} from Stash")
                    result = await resp.json()
                    if "errors" in result:
                        raise MediaSourceError(f"GraphQL errors: {result['errors']}")
                    return result.get("data", {})
        except MediaSourceError:
            raise
        except Exception as err:
            raise MediaSourceError(f"Error querying Stash: {err}") from err

    def _gallery_thumb(self, gallery_id: str) -> str:
        url, api_key = self._config()
        return f"{url}/gallery/{gallery_id}/cover?apikey={api_key}"

    def _image_thumb(self, image_id: str) -> str:
        url, api_key = self._config()
        return f"{url}/image/{image_id}/thumbnail?apikey={api_key}"

    def _image_full(self, image_id: str) -> str:
        url, api_key = self._config()
        return f"{url}/image/{image_id}/image?apikey={api_key}"

    def _scene_thumb(self, scene_id: str) -> str:
        url, api_key = self._config()
        return f"{url}/scene/{scene_id}/screenshot?apikey={api_key}"

    def _scene_stream(self, scene_id: str) -> str:
        url, api_key = self._config()
        return f"{url}/scene/{scene_id}/stream?apikey={api_key}"

    # ------------------------------------------------------------------
    # Required MediaSource methods
    # ------------------------------------------------------------------

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve an image or scene identifier to a playable URL."""
        identifier = item.identifier or ""
        parts = identifier.split("/")
        section = parts[0]
        item_id = parts[1] if len(parts) > 1 else None

        if not item_id:
            raise MediaSourceError(f"Cannot resolve media: {identifier}")

        if section == "images":
            media_url = self._image_full(item_id)
            default_mime = "image/jpeg"
        elif section == "scenes":
            media_url = self._scene_stream(item_id)
            default_mime = "video/mp4"
        else:
            raise MediaSourceError(f"Cannot resolve media: {identifier}")

        # Probe the actual content-type
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    media_url, timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    mime = resp.content_type or default_mime
        except Exception:
            mime = default_mime

        return PlayMedia(media_url, mime)

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Return the browseable media tree for the given item."""
        identifier = item.identifier or ""

        if not identifier:
            return self._build_root()

        parts = identifier.split("/")
        section = parts[0]
        item_id = parts[1] if len(parts) > 1 else None

        if section == "galleries":
            return (
                await self._browse_gallery(item_id)
                if item_id
                else await self._browse_galleries()
            )
        if section == "scenes":
            return await self._browse_scenes()

        return self._build_root()

    # ------------------------------------------------------------------
    # Browse helpers
    # ------------------------------------------------------------------

    def _build_root(self) -> BrowseMediaSource:
        """Return the top-level Stash node."""
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier="",
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.IMAGE,
            title="Stash",
            can_play=False,
            can_expand=True,
            children=[
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier="scenes",
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.VIDEO,
                    title="Scenes",
                    can_play=False,
                    can_expand=True,
                ),
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier="galleries",
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.IMAGE,
                    title="Galleries",
                    can_play=False,
                    can_expand=True,
                ),
            ],
        )

    async def _browse_scenes(self) -> BrowseMediaSource:
        """Return the 48 most recent scenes."""
        data = await self._query("""
            query {
                findScenes(filter: { per_page: 48, sort: "date", direction: DESC }) {
                    scenes { id title date }
                }
            }
        """)
        scenes = (data.get("findScenes") or {}).get("scenes", [])
        children = [
            BrowseMediaSource(
                domain=DOMAIN,
                identifier=f"scenes/{s.get('id')}",
                media_class=MediaClass.VIDEO,
                media_content_type=MediaType.VIDEO,
                title=(
                    f"{s.get('title') or 'Scene'}"
                    + (f" ({s.get('date')})" if s.get("date") else "")
                ),
                can_play=True,
                can_expand=False,
                thumbnail=self._scene_thumb(s.get("id", "")),
            )
            for s in scenes
        ]
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier="scenes",
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="Scenes",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _browse_galleries(self) -> BrowseMediaSource:
        """Return all galleries sorted by date."""
        data = await self._query("""
            query {
                findGalleries(filter: { per_page: 100, sort: "date", direction: DESC }) {
                    galleries { id title date image_count }
                }
            }
        """)
        galleries = (data.get("findGalleries") or {}).get("galleries", [])
        children = [
            BrowseMediaSource(
                domain=DOMAIN,
                identifier=f"galleries/{g.get('id')}",
                media_class=MediaClass.ALBUM,
                media_content_type=MediaType.IMAGE,
                title=(
                    f"{g.get('title') or 'Gallery'}"
                    f" ({g.get('image_count', 0)} images)"
                    + (f" \u2014 {g.get('date')}" if g.get("date") else "")
                ),
                can_play=False,
                can_expand=True,
                thumbnail=self._gallery_thumb(g.get("id", "")),
            )
            for g in galleries
        ]
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier="galleries",
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.IMAGE,
            title="Galleries",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _browse_gallery(self, gallery_id: str) -> BrowseMediaSource:
        """Return images within a specific gallery."""
        data = await self._query(f"""
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
        """)
        images = (data.get("findImages") or {}).get("images", [])
        title = (data.get("findGallery") or {}).get("title") or "Gallery"
        children = [
            BrowseMediaSource(
                domain=DOMAIN,
                identifier=f"images/{img.get('id')}",
                media_class=MediaClass.IMAGE,
                media_content_type=MediaType.IMAGE,
                title=img.get("title") or f"Image {img.get('id')}",
                can_play=True,
                can_expand=False,
                thumbnail=self._image_thumb(img.get("id", "")),
            )
            for img in images
        ]
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=f"galleries/{gallery_id}",
            media_class=MediaClass.ALBUM,
            media_content_type=MediaType.IMAGE,
            title=title,
            can_play=False,
            can_expand=True,
            thumbnail=self._gallery_thumb(gallery_id),
            children=children,
        )
