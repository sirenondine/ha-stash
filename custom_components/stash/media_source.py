"""Media source platform for Stash — scenes, galleries and images."""

from __future__ import annotations

import logging

import aiohttp
from aiohttp.web import HTTPNotFound, Request, Response, StreamResponse
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.media_player import MediaClass, MediaType
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceError,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_API_KEY, CONF_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_get_media_source(hass: HomeAssistant) -> StashMediaSource:
    """Return the Stash media source and register the proxy view."""
    hass.http.register_view(StashMediaView(hass))
    return StashMediaSource(hass)


# ---------------------------------------------------------------------------
# HA HTTP view — proxies Stash images through HA so they work remotely
# and without exposing the API key to the browser
# ---------------------------------------------------------------------------


class StashMediaView(HomeAssistantView):
    """Proxy Stash thumbnails and images through HA's HTTP server."""

    url = "/stash/{entry_id}/{resource_type}/{item_id}/{size}"
    name = "stash_media"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialise the view."""
        self.hass = hass

    async def get(
        self,
        request: Request,
        entry_id: str,
        resource_type: str,
        item_id: str,
        size: str,
    ) -> Response | StreamResponse:
        """Proxy a GET request to Stash, streaming video chunk-by-chunk."""
        entry = self.hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            raise HTTPNotFound

        stash_base = entry.data[CONF_URL]
        api_key = entry.data[CONF_API_KEY]
        target = f"{stash_base}/{resource_type}/{item_id}/{size}?apikey={api_key}"

        session = async_get_clientsession(self.hass)
        try:
            resp = await session.get(target, timeout=aiohttp.ClientTimeout(total=None))
        except aiohttp.ClientError as err:
            _LOGGER.debug("Error connecting to Stash: %s", err)
            raise HTTPNotFound from err

        if resp.status != 200:
            raise HTTPNotFound

        content_type = resp.content_type or "application/octet-stream"

        # Stream video chunk-by-chunk so HA never buffers the whole file
        if content_type.startswith("video/"):
            stream = StreamResponse()
            stream.content_type = content_type
            await stream.prepare(request)
            async for chunk in resp.content.iter_chunked(65536):
                await stream.write(chunk)
            return stream

        # Images and thumbnails — read fully and return
        try:
            body = await resp.read()
        except aiohttp.ClientError as err:
            raise HTTPNotFound from err
        return Response(body=body, content_type=content_type)


# ---------------------------------------------------------------------------
# Media source
# ---------------------------------------------------------------------------


class StashMediaSource(MediaSource):
    """Expose Stash scenes, galleries and images in HA's global media browser."""

    name = "Stash"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialise."""
        super().__init__(DOMAIN)
        self.hass = hass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _entry_id(self) -> str:
        """Return the entry_id of the first active config entry."""
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            return entry.entry_id
        raise MediaSourceError("No active Stash config entry found")

    def _stash_config(self) -> tuple[str, str]:
        """Return (url, api_key) for direct stream URLs."""
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            return entry.data[CONF_URL], entry.data[CONF_API_KEY]
        raise MediaSourceError("No active Stash config entry found")

    def _proxy(self, resource_type: str, item_id: str, size: str) -> str:
        """Return a HA-proxied URL for a Stash media asset."""
        return f"/stash/{self._entry_id()}/{resource_type}/{item_id}/{size}"

    async def _query(self, query: str) -> dict:
        """Execute a GraphQL query against Stash."""
        url, api_key = self._stash_config()
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

    # ------------------------------------------------------------------
    # Required MediaSource methods
    # ------------------------------------------------------------------

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve a scene or image to a playable/displayable URL."""
        identifier = item.identifier or ""
        parts = identifier.split("/")
        section = parts[0]
        item_id = parts[1] if len(parts) > 1 else None

        if not item_id:
            raise Unresolvable(f"Cannot resolve media: {identifier}")

        if section == "scenes":
            # Stream via the HA proxy view so it works behind a reverse proxy.
            # The view streams chunk-by-chunk so HA never buffers the full file.
            return PlayMedia(
                self._proxy("scene", item_id, "stream"),
                "video/mp4",
            )

        if section == "images":
            # Images served via the HA proxy view.
            # Returning image/* MIME type tells HA to display with <img>, not <video>.
            proxy_url = self._proxy("image", item_id, "image")
            return PlayMedia(proxy_url, "image/jpeg")

        raise Unresolvable(f"Cannot resolve media: {identifier}")

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Return the browseable media tree."""
        identifier = item.identifier or ""

        if not identifier:
            return self._build_root()

        parts = identifier.split("/")
        section = parts[0]
        item_id = parts[1] if len(parts) > 1 else None

        if section == "scenes":
            return await self._browse_scenes()
        if section == "galleries":
            return (
                await self._browse_gallery(item_id)
                if item_id
                else await self._browse_galleries()
            )

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
            media_content_type=MediaType.VIDEO,
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
                thumbnail=self._proxy("scene", s.get("id", ""), "screenshot"),
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
                thumbnail=self._proxy("gallery", g.get("id", ""), "cover"),
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
                # Images are not "playable" via video element — they browse only.
                # Thumbnails load via the HA proxy view so they work locally & remotely.
                can_play=False,
                can_expand=False,
                thumbnail=self._proxy("image", img.get("id", ""), "thumbnail"),
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
            thumbnail=self._proxy("gallery", gallery_id, "cover"),
            children=children,
        )
