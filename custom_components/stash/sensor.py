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
)
from .coordinator import StashDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Stash sensors."""
    coordinator: StashDataUpdateCoordinator = entry.runtime_data

    sensors = [
        # Count sensors
        StashCountSensor(coordinator, entry, SENSOR_SCENE_COUNT),
        StashCountSensor(coordinator, entry, SENSOR_PERFORMER_COUNT),
        StashCountSensor(coordinator, entry, SENSOR_STUDIO_COUNT),
        StashCountSensor(coordinator, entry, SENSOR_GROUP_COUNT),
        StashCountSensor(coordinator, entry, SENSOR_TAG_COUNT),
        StashCountSensor(coordinator, entry, SENSOR_GALLERY_COUNT),
        StashCountSensor(coordinator, entry, SENSOR_IMAGE_COUNT),
        StashCountSensor(coordinator, entry, SENSOR_TOTAL_O_COUNT),
        StashCountSensor(coordinator, entry, SENSOR_TOTAL_PLAY_COUNT),
        StashCountSensor(coordinator, entry, SENSOR_SCENES_PLAYED),
        # Size sensors
        StashSizeSensor(coordinator, entry, SENSOR_SCENES_SIZE),
        StashSizeSensor(coordinator, entry, SENSOR_IMAGES_SIZE),
        # Duration sensors
        StashDurationSensor(coordinator, entry, SENSOR_SCENES_DURATION),
        StashDurationSensor(coordinator, entry, SENSOR_TOTAL_PLAY_DURATION),
    ]

    async_add_entities(sensors)


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return shared device info for all Stash sensors."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Stash",
        manufacturer="Stash",
        entry_type=DeviceEntryType.SERVICE,
    )


class StashCountSensor(CoordinatorEntity[StashDataUpdateCoordinator], SensorEntity):
    """Representation of a Stash count sensor."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(
        self,
        coordinator: StashDataUpdateCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type

        sensor_info = SENSOR_TYPES[sensor_type]
        self._attr_name = sensor_info["name"]
        self._attr_icon = sensor_info["icon"]
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._sensor_type)


class StashSizeSensor(CoordinatorEntity[StashDataUpdateCoordinator], SensorEntity):
    """Representation of a Stash file size sensor (bytes → GB)."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = UnitOfInformation.GIGABYTES

    def __init__(
        self,
        coordinator: StashDataUpdateCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type

        sensor_info = SENSOR_TYPES[sensor_type]
        self._attr_name = sensor_info["name"]
        self._attr_icon = sensor_info["icon"]
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor in GB."""
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.get(self._sensor_type)
        if raw is None:
            return None
        return round(raw / (1024**3), 2)


class StashDurationSensor(CoordinatorEntity[StashDataUpdateCoordinator], SensorEntity):
    """Representation of a Stash duration sensor (seconds → hours)."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = UnitOfTime.HOURS

    def __init__(
        self,
        coordinator: StashDataUpdateCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type

        sensor_info = SENSOR_TYPES[sensor_type]
        self._attr_name = sensor_info["name"]
        self._attr_icon = sensor_info["icon"]
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor in hours."""
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.get(self._sensor_type)
        if raw is None:
            return None
        return round(raw / 3600, 2)
