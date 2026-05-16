"""The Stash integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_FAST_INTERVAL,
    CONF_SLOW_INTERVAL,
    DEFAULT_FAST_INTERVAL,
    DEFAULT_SLOW_INTERVAL,
)
from .coordinator import StashStatsCoordinator, StashStatusCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]


@dataclass
class StashRuntimeData:
    """Runtime data stored on the config entry."""

    stats_coordinator: StashStatsCoordinator
    status_coordinator: StashStatusCoordinator


type StashConfigEntry = ConfigEntry[StashRuntimeData]


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: StashConfigEntry) -> bool:
    """Set up Stash from a config entry."""
    slow_interval = entry.options.get(CONF_SLOW_INTERVAL, DEFAULT_SLOW_INTERVAL)
    fast_interval = entry.options.get(CONF_FAST_INTERVAL, DEFAULT_FAST_INTERVAL)

    stats_coordinator = StashStatsCoordinator(hass, entry, slow_interval)
    status_coordinator = StashStatusCoordinator(hass, entry, fast_interval)

    await stats_coordinator.async_config_entry_first_refresh()
    await status_coordinator.async_config_entry_first_refresh()

    entry.runtime_data = StashRuntimeData(
        stats_coordinator=stats_coordinator,
        status_coordinator=status_coordinator,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_setup_services(hass)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        async_unload_services(hass)
    return unload_ok
