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
    SENSOR_IMAGE_COUNT,
    SENSOR_MOVIE_COUNT,
    SENSOR_PERFORMER_COUNT,
    SENSOR_SCENE_COUNT,
    SENSOR_STUDIO_COUNT,
    SENSOR_TAG_COUNT,
    SENSOR_TOTAL_DURATION,
    SENSOR_TOTAL_SIZE,
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
        StashCountSensor(coordinator, entry, SENSOR_SCENE_COUNT),
        StashCountSensor(coordinator, entry, SENSOR_PERFORMER_COUNT),
        StashCountSensor(coordinator, entry, SENSOR_STUDIO_COUNT),
        StashCountSensor(coordinator, entry, SENSOR_MOVIE_COUNT),
        StashCountSensor(coordinator, entry, SENSOR_TAG_COUNT),
        StashCountSensor(coordinator, entry, SENSOR_GALLERY_COUNT),
        StashCountSensor(coordinator, entry, SENSOR_IMAGE_COUNT),
        StashSizeSensor(coordinator, entry),
        StashDurationSensor(coordinator, entry),
    ]

    async_add_entities(sensors)


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
        self._entry = entry

        sensor_info = SENSOR_TYPES[sensor_type]
        self._attr_name = sensor_info["name"]
        self._attr_icon = sensor_info["icon"]
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Stash",
            manufacturer="Stash",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None

        # Map sensor type to API field name
        field_mapping = {
            SENSOR_SCENE_COUNT: "sceneCount",
            SENSOR_PERFORMER_COUNT: "performerCount",
            SENSOR_STUDIO_COUNT: "studioCount",
            SENSOR_MOVIE_COUNT: "movieCount",
            SENSOR_TAG_COUNT: "tagCount",
            SENSOR_GALLERY_COUNT: "galleryCount",
            SENSOR_IMAGE_COUNT: "imageCount",
        }

        field_name = field_mapping.get(self._sensor_type)
        if field_name and field_name in self.coordinator.data:
            return self.coordinator.data[field_name]
        return None


class StashSizeSensor(CoordinatorEntity[StashDataUpdateCoordinator], SensorEntity):
    """Representation of a Stash size sensor."""

    _attr_has_entity_name = True
    _attr_name = "Total Size"
    _attr_icon = "mdi:database"
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(
        self,
        coordinator: StashDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_TOTAL_SIZE}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Stash",
            manufacturer="Stash",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None

        total_size = self.coordinator.data.get("totalSize")
        if total_size is None:
            return None

        # totalSize is in bytes, convert to GB
        return round(total_size / (1024**3), 2)

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return UnitOfInformation.GIGABYTES


class StashDurationSensor(CoordinatorEntity[StashDataUpdateCoordinator], SensorEntity):
    """Representation of a Stash duration sensor."""

    _attr_has_entity_name = True
    _attr_name = "Total Duration"
    _attr_icon = "mdi:clock-outline"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(
        self,
        coordinator: StashDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_TOTAL_DURATION}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Stash",
            manufacturer="Stash",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None

        total_duration = self.coordinator.data.get("totalDuration")
        if total_duration is None:
            return None

        # totalDuration is in seconds, convert to hours
        return round(total_duration / 3600, 2)

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return UnitOfTime.HOURS
