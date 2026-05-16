"""Binary sensor platform for Stash integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BINARY_SENSOR_DLNA,
    BINARY_SENSOR_JOB_RUNNING,
    BINARY_SENSOR_ONLINE,
    BINARY_SENSOR_UPDATE_AVAILABLE,
    DOMAIN,
)
from .coordinator import StashStatusCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Stash binary sensors."""
    coordinator: StashStatusCoordinator = entry.runtime_data.status_coordinator

    async_add_entities(
        [
            StashOnlineBinarySensor(coordinator, entry),
            StashJobRunningBinarySensor(coordinator, entry),
            StashUpdateAvailableBinarySensor(coordinator, entry),
            StashDLNABinarySensor(coordinator, entry),
        ]
    )


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return shared device info for all Stash binary sensors."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Stash",
        manufacturer="Stash",
        entry_type=DeviceEntryType.SERVICE,
    )


class StashOnlineBinarySensor(
    CoordinatorEntity[StashStatusCoordinator], BinarySensorEntity
):
    """Binary sensor: is Stash reachable?"""

    _attr_has_entity_name = True
    _attr_name = "Online"
    _attr_icon = "mdi:server-network"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: StashStatusCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{BINARY_SENSOR_ONLINE}"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success


class StashJobRunningBinarySensor(
    CoordinatorEntity[StashStatusCoordinator], BinarySensorEntity
):
    """Binary sensor: is a Stash job currently running?"""

    _attr_has_entity_name = True
    _attr_name = "Job Running"
    _attr_icon = "mdi:cog-sync"
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: StashStatusCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{BINARY_SENSOR_JOB_RUNNING}"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return any(
            j.get("status") == "RUNNING" for j in self.coordinator.data.get("jobs", [])
        )

    @property
    def extra_state_attributes(self) -> dict | None:
        if self.coordinator.data is None:
            return None
        running = [
            j
            for j in self.coordinator.data.get("jobs", [])
            if j.get("status") == "RUNNING"
        ]
        if running:
            return {
                "description": running[0].get("description"),
                "progress": running[0].get("progress"),
            }
        return None


class StashUpdateAvailableBinarySensor(
    CoordinatorEntity[StashStatusCoordinator], BinarySensorEntity
):
    """Binary sensor: is a newer version of Stash available?"""

    _attr_has_entity_name = True
    _attr_name = "Update Available"
    _attr_icon = "mdi:update"
    _attr_device_class = BinarySensorDeviceClass.UPDATE
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: StashStatusCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{BINARY_SENSOR_UPDATE_AVAILABLE}"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        version = self.coordinator.data.get("version")
        latest = self.coordinator.data.get("latest_version")
        if not version or not latest:
            return None
        return version != latest

    @property
    def extra_state_attributes(self) -> dict | None:
        if self.coordinator.data is None:
            return None
        return {
            "current_version": self.coordinator.data.get("version"),
            "latest_version": self.coordinator.data.get("latest_version"),
        }


class StashDLNABinarySensor(
    CoordinatorEntity[StashStatusCoordinator], BinarySensorEntity
):
    """Binary sensor: is Stash DLNA currently running?"""

    _attr_has_entity_name = True
    _attr_name = "DLNA"
    _attr_icon = "mdi:cast"
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: StashStatusCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{BINARY_SENSOR_DLNA}"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("dlna_running", False)
