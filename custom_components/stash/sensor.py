"""Sensor platform for Stash integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfInformation, UnitOfTime
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
            StashActiveJobSensor(status, entry),
            # --- Version sensor (slow coordinator — avoids GitHub rate limits) ---
            StashVersionSensor(stats, entry),
            # --- Scene sensors (slow coordinator) ---
            StashLastOSceneSensor(stats, entry),
            StashLastWatchedSceneSensor(stats, entry),
            # --- Performer sensors (slow coordinator) ---
            StashTopPerformerSensor(stats, entry),
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


class StashVersionSensor(CoordinatorEntity[StashStatsCoordinator], SensorEntity):
    """Sensor showing the current Stash server version."""

    _attr_has_entity_name = True
    _attr_name = "Version"
    _attr_icon = "mdi:tag-text"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: StashStatsCoordinator, entry: ConfigEntry) -> None:
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
    _attr_entity_category = EntityCategory.DIAGNOSTIC

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


class StashLastOSceneSensor(CoordinatorEntity[StashStatsCoordinator], SensorEntity):
    """Sensor showing the title of the most recently O'd scene."""

    _attr_has_entity_name = True
    _attr_name = "Last O Scene"
    _attr_icon = "mdi:movie-star"

    def __init__(self, coordinator: StashStatsCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_last_o_scene"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> str | None:
        """Return the title of the most recently O'd scene."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("last_o_scene_title")

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return scene details as attributes."""
        if self.coordinator.data is None:
            return None
        title = self.coordinator.data.get("last_o_scene_title")
        if title is None:
            return None
        return {
            "date": self.coordinator.data.get("last_o_scene_date"),
            "o_count": self.coordinator.data.get("last_o_scene_o_count"),
            "last_o_at": self.coordinator.data.get("last_o_scene_last_o_at"),
        }


class StashLastWatchedSceneSensor(
    CoordinatorEntity[StashStatsCoordinator], SensorEntity
):
    """Sensor showing the title of the most recently watched scene."""

    _attr_has_entity_name = True
    _attr_name = "Last Watched Scene"
    _attr_icon = "mdi:television-play"

    def __init__(self, coordinator: StashStatsCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_last_watched_scene"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> str | None:
        """Return the title of the most recently watched scene."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("last_watched_scene_title")

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return scene details as attributes."""
        if self.coordinator.data is None:
            return None
        title = self.coordinator.data.get("last_watched_scene_title")
        if title is None:
            return None
        return {
            "date": self.coordinator.data.get("last_watched_scene_date"),
            "play_count": self.coordinator.data.get("last_watched_scene_play_count"),
            "last_played_at": self.coordinator.data.get(
                "last_watched_scene_last_played_at"
            ),
        }


class StashTopPerformerSensor(CoordinatorEntity[StashStatsCoordinator], SensorEntity):
    """Sensor showing the top performer by scene count."""

    _attr_has_entity_name = True
    _attr_name = "Top Performer"
    _attr_icon = "mdi:account-star"

    def __init__(self, coordinator: StashStatsCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_top_performer"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> str | None:
        """Return the name of the #1 performer by scene count."""
        if self.coordinator.data is None:
            return None
        performers = self.coordinator.data.get("top_performers", [])
        if not performers:
            return None
        return performers[0].get("name")

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return the full top 5 performer list as attributes."""
        if self.coordinator.data is None:
            return None
        performers = self.coordinator.data.get("top_performers", [])
        if not performers:
            return None
        return {"top_performers": performers}
