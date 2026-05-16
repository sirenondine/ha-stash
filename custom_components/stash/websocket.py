"""WebSocket client for real-time Stash job updates."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable

import aiohttp
from homeassistant.core import HomeAssistant

from .coordinator import StashStatusCoordinator

_LOGGER = logging.getLogger(__name__)

_JOBS_SUBSCRIPTION = (
    "subscription { jobsSubscribe { type job { id status description progress } } }"
)

# Reconnect back-off delays in seconds
_RETRY_DELAYS = [5, 10, 30, 60, 120, 300]


class StashWebSocketClient:
    """Manages a persistent WebSocket connection to Stash for real-time updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        url: str,
        api_key: str,
        status_coordinator: StashStatusCoordinator,
    ) -> None:
        """Initialise the client."""
        self._hass = hass
        self._ws_url = (
            url.replace("http://", "ws://").replace("https://", "wss://") + "/graphql"
        )
        self._api_key = api_key
        self._coordinator = status_coordinator
        self._connected = False
        self._running = False
        self._task: asyncio.Task | None = None
        self._callbacks: set[Callable[[], None]] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def connected(self) -> bool:
        """Return True when the WebSocket is connected and subscribed."""
        return self._connected

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback that fires whenever connection state changes."""
        self._callbacks.add(callback)

    def unregister_callback(self, callback: Callable[[], None]) -> None:
        """Remove a previously registered callback."""
        self._callbacks.discard(callback)

    async def async_start(self) -> None:
        """Start the background WebSocket listener task."""
        self._running = True
        self._task = self._hass.async_create_background_task(
            self._run_forever(),
            name="stash_websocket",
        )
        _LOGGER.debug("Stash WebSocket task started")

    async def async_stop(self) -> None:
        """Stop the WebSocket listener and clean up."""
        self._running = False
        self._set_connected(False)
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        _LOGGER.debug("Stash WebSocket task stopped")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_connected(self, connected: bool) -> None:
        """Update connection state and notify any registered callbacks."""
        if self._connected == connected:
            return
        self._connected = connected
        _LOGGER.debug("Stash WebSocket connected=%s", connected)
        for cb in self._callbacks:
            cb()

    async def _run_forever(self) -> None:
        """Connect and reconnect until async_stop() is called."""
        retry_index = 0
        while self._running:
            try:
                await self._connect_and_listen()
                retry_index = 0
            except asyncio.CancelledError:
                break
            except Exception as err:  # pylint: disable=broad-except
                self._set_connected(False)
                delay = _RETRY_DELAYS[min(retry_index, len(_RETRY_DELAYS) - 1)]
                retry_index += 1
                _LOGGER.warning(
                    "Stash WebSocket disconnected (%s). Reconnecting in %d s.",
                    err,
                    delay,
                )
                if self._running:
                    await asyncio.sleep(delay)

    async def _connect_and_listen(self) -> None:
        """Open the WebSocket, subscribe to jobs, and process messages."""
        _LOGGER.debug("Connecting to Stash WebSocket: %s", self._ws_url)
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                self._ws_url,
                headers={"ApiKey": self._api_key},
                protocols=["graphql-transport-ws"],
                heartbeat=30,
            ) as ws:
                # Initiate the graphql-transport-ws handshake
                await ws.send_str(
                    json.dumps({"type": "connection_init", "payload": {}})
                )

                async for msg in ws:
                    if not self._running:
                        await ws.close()
                        return
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await self._handle_message(ws, json.loads(msg.data))
                    elif msg.type in (
                        aiohttp.WSMsgType.ERROR,
                        aiohttp.WSMsgType.CLOSED,
                    ):
                        break

        self._set_connected(False)

    async def _handle_message(
        self, ws: aiohttp.ClientWebSocketResponse, msg: dict
    ) -> None:
        """Dispatch a single WebSocket message."""
        msg_type = msg.get("type")

        if msg_type == "connection_ack":
            # Handshake complete — subscribe to job updates
            self._set_connected(True)
            await ws.send_str(
                json.dumps(
                    {
                        "type": "subscribe",
                        "id": "jobs",
                        "payload": {"query": _JOBS_SUBSCRIPTION},
                    }
                )
            )

        elif msg_type == "next":
            # A subscription event arrived
            payload = (msg.get("payload") or {}).get("data", {})
            if "jobsSubscribe" in payload:
                _LOGGER.debug("Job update via WebSocket: %s", payload["jobsSubscribe"])
                # Trigger an immediate status coordinator refresh
                self._hass.async_create_task(self._coordinator.async_request_refresh())

        elif msg_type == "ping":
            # Respond to server keepalives
            await ws.send_str(json.dumps({"type": "pong"}))

        elif msg_type in ("error", "connection_error"):
            _LOGGER.error(
                "Stash WebSocket error (type=%s): %s", msg_type, msg.get("payload")
            )
