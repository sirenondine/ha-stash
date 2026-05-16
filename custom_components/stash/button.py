"""Button platform for Stash integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


@dataclass(frozen=True)
class StashButtonDescription(ButtonEntityDescription):
    """Describes a Stash button entity."""

    service: str = ""


BUTTONS: tuple[StashButtonDescription, ...] = (
    StashButtonDescription(
        key="scan",
        name="Scan Library",
        icon="mdi:magnify-scan",
        service="scan",
    ),
    StashButtonDescription(
        key="generate",
        name="Generate Metadata",
        icon="mdi:image-sync",
        service="generate",
    ),
    StashButtonDescription(
        key="autotag",
        name="Auto Tag",
        icon="mdi:tag-plus",
        service="autotag",
    ),
    StashButtonDescription(
        key="clean",
        name="Clean Library",
        icon="mdi:broom",
        service="clean",
    ),
    StashButtonDescription(
        key="identify",
        name="Identify Scenes",
        icon="mdi:magnify",
        service="identify",
    ),
    StashButtonDescription(
        key="backup",
        name="Backup Database",
        icon="mdi:database-export",
        service="backup",
    ),
    StashButtonDescription(
        key="optimise",
        name="Optimise Database",
        icon="mdi:database-cog",
        service="optimise",
    ),
    StashButtonDescription(
        key="stop_all_jobs",
        name="Stop All Jobs",
        icon="mdi:stop-circle-outline",
        service="stop_all_jobs",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Stash button entities."""
    async_add_entities(StashButton(entry, description) for description in BUTTONS)


class StashButton(ButtonEntity):
    """A button that triggers a Stash service."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry,
        description: StashButtonDescription,
    ) -> None:
        """Initialize the button."""
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._service = description.service
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Stash",
            manufacturer="Stash",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_press(self) -> None:
        """Handle the button press by calling the matching Stash service."""
        await self.hass.services.async_call(DOMAIN, self._service)
