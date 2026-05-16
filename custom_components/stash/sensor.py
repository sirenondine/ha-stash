"""Sensor platform for Stash integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfInformation, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SENSOR_ACTIVE_JOB,
    SENSOR_GALLERY_COUNT,
    SENSOR_GROUP_COUNT,
    SENSOR_IMAGE_COUNT,
    SENSOR_IMAGES_SIZE,
    SENSOR_PERFORMER_COUNT,
    SENSOR_SCENE_COUNT,
    SENSOR_SCENES_DURATION,
    SENSOR_SCENES_PLAYED,
    SENSOR_SCENES_SIZE,
    SENSOR_STUDIO_COUNT,
    SENSOR_TAG_COUNT,
    SENSOR_TOTAL_O_COUNT,
    SENSOR_TOTAL_PLAY_COUNT,
    SENSOR_TOTAL_PLAY_DURATION,
    SENSOR_TYPES,
    SENSOR_VERSION,
)
from .coordinator import StashStatsCoordinator, StashStatusCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Stash sensors."""
    stats = entry.runtime_data.stats_coordinator
    status = entry.runtime_data.status_coordinator

    async_add_entities(
        [
            # --- Stats sensors (slow coordinator) ---
            StashCountSensor(stats, entry, SENSOR_SCENE_COUNT),
            StashCountSensor(stats, entry, SENSOR_PERFORMER_COUNT),
            StashCountSensor(stats, entry, SENSOR_STUDIO_COUNT),
            StashCountSensor(stats, entry, SENSOR_GROUP_COUNT),
            StashCountSensor(stats, entry, SENSOR_TAG_COUNT),
            StashCountSensor(stats, entry, SENSOR_GALLERY_COUNT),
            StashCountSensor(stats, entry, SENSOR_IMAGE_COUNT),
            StashCountSensor(stats, entry, SENSOR_TOTAL_O_COUNT),
            StashCountSensor(stats, entry, SENSOR_TOTAL_PLAY_COUNT),
            StashCountSensor(stats, entry, SENSOR_SCENES_PLAYED),
            StashSizeSensor(stats, entry, SENSOR_SCENES_SIZE),
            StashSizeSensor(stats, entry, SENSOR_IMAGES_SIZE),
            StashDurationSensor(stats, entry, SENSOR_SCENES_DURATION),
            StashDurationSensor(stats, entry, SENSOR_TOTAL_PLAY_DURATION),
            # --- Status sensors (fast coordinator) ---
            StashVersionSensor(status, entry),
            StashActiveJobSensor(status, entry),
        ]
    )


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return shared device info for all Stash sensors."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Stash",
        manufacturer="Stash",
        entry_type=DeviceEntryType.SERVICE,
    )


class StashCountSensor(CoordinatorEntity[StashStatsCoordinator], SensorEntity):
    """A sensor showing an integer count from the Stash library stats."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(
        self,
        coordinator: StashStatsCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
    ) -> None:
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        info = SENSOR_TYPES[sensor_type]
        self._attr_name = info["name"]
        self._attr_icon = info["icon"]
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._sensor_type)


class StashSizeSensor(CoordinatorEntity[StashStatsCoordinator], SensorEntity):
    """A sensor showing a file size in GB from the Stash library stats."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = UnitOfInformation.GIGABYTES

    def __init__(
        self,
        coordinator: StashStatsCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
    ) -> None:
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        info = SENSOR_TYPES[sensor_type]
        self._attr_name = info["name"]
        self._attr_icon = info["icon"]
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.get(self._sensor_type)
        if raw is None:
            return None
        return round(raw / (1024**3), 2)


class StashDurationSensor(CoordinatorEntity[StashStatsCoordinator], SensorEntity):
    """A sensor showing a duration in hours from the Stash library stats."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = UnitOfTime.HOURS

    def __init__(
        self,
        coordinator: StashStatsCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
    ) -> None:
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        info = SENSOR_TYPES[sensor_type]
        self._attr_name = info["name"]
        self._attr_icon = info["icon"]
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.get(self._sensor_type)
        if raw is None:
            return None
        return round(raw / 3600, 2)


class StashVersionSensor(CoordinatorEntity[StashStatusCoordinator], SensorEntity):
    """Sensor showing the current Stash server version."""

    _attr_has_entity_name = True
    _attr_name = "Version"
    _attr_icon = "mdi:tag-text"

    def __init__(self, coordinator: StashStatusCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_VERSION}"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("version")


class StashActiveJobSensor(CoordinatorEntity[StashStatusCoordinator], SensorEntity):
    """Sensor showing the currently active Stash job, or Idle."""

    _attr_has_entity_name = True
    _attr_name = "Active Job"
    _attr_icon = "mdi:cog-sync"

    def __init__(self, coordinator: StashStatusCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_ACTIVE_JOB}"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> str:
        if self.coordinator.data is None:
            return "Unknown"
        jobs = self.coordinator.data.get("jobs", [])
        running = [j for j in jobs if j.get("status") == "RUNNING"]
        if running:
            return running[0].get("description", "Running")
        return "Idle"

    @property
    def extra_state_attributes(self) -> dict | None:
        if self.coordinator.data is None:
            return None
        jobs = self.coordinator.data.get("jobs", [])
        running = [j for j in jobs if j.get("status") == "RUNNING"]
        if running:
            job = running[0]
            return {
                "progress": job.get("progress"),
                "job_id": job.get("id"),
            }
        return None
