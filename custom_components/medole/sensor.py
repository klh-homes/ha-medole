"""Sensor platform for Medole Dehumidifier integration."""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_NAME,
    DOMAIN,
    REG_DEHUMIDIFY_MODE,
    REG_FAN_ALARM_HOURS,
    REG_FAN_OPERATION_HOURS,
    REG_HUMIDITY_1,
    REG_HUMIDITY_2,
    REG_OPERATION_STATUS,
    REG_PIPE_TEMPERATURE,
    REG_PURIFY_MODE,
    REG_TEMPERATURE_1,
    REG_TEMPERATURE_2,
    STATUS_COMPRESSOR_ON,
    STATUS_FAN_ON,
    STATUS_HIGH_PRESSURE_ERROR,
    STATUS_HUMIDITY_SENSOR_ERROR,
    STATUS_LOW_PRESSURE_ERROR,
    STATUS_PIPE_TEMP_ERROR,
    STATUS_ROOM_TEMP_ERROR,
    STATUS_WATER_FULL_ERROR,
)
from .coordinator import MedoleDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Medole Dehumidifier sensor platform."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = data["coordinator"]
    name = data["config"][CONF_NAME]

    entities = [
        MedoleTemperatureSensor(coordinator, name, 1),
        MedoleHumiditySensor(coordinator, name, 1),
        MedolePipeTemperatureSensor(coordinator, name),
        MedoleFanOperationHoursSensor(coordinator, name),
        MedoleFanAlarmHoursSensor(coordinator, name),
        MedoleStatusSensor(coordinator, name),
    ]
    async_add_entities(entities)


class MedoleBaseSensor(CoordinatorEntity[MedoleDataCoordinator], SensorEntity):
    """Base class for Medole Dehumidifier sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MedoleDataCoordinator,
        name: str,
        sensor_type: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{name}_{sensor_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{name}_humidifier")},
            "name": name,
            "manufacturer": "Medole",
            "model": "IN-D17",
        }


def _decode_temperature(register_value: int) -> float:
    """Temperature format: lo-byte = integer degrees, hi-byte = 0.1°C decimal."""
    integer_part = register_value & 0xFF
    decimal_part = (register_value >> 8) & 0xFF
    return integer_part + decimal_part / 10


class MedoleTemperatureSensor(MedoleBaseSensor):
    """Representation of a Medole Temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        coordinator: MedoleDataCoordinator,
        name: str,
        sensor_number: int,
    ) -> None:
        super().__init__(coordinator, name, f"temperature_{sensor_number}")
        self._attr_name = "Temperature"
        self._register = (
            REG_TEMPERATURE_1 if sensor_number == 1 else REG_TEMPERATURE_2
        )

    @property
    def native_value(self) -> float | None:
        raw = (self.coordinator.data or {}).get(self._register)
        return _decode_temperature(raw) if raw is not None else None


class MedoleHumiditySensor(MedoleBaseSensor):
    """Representation of a Medole Humidity sensor."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(
        self,
        coordinator: MedoleDataCoordinator,
        name: str,
        sensor_number: int,
    ) -> None:
        super().__init__(coordinator, name, f"humidity_{sensor_number}")
        self._attr_name = "Humidity"
        self._register = (
            REG_HUMIDITY_1 if sensor_number == 1 else REG_HUMIDITY_2
        )

    @property
    def native_value(self) -> int | None:
        return (self.coordinator.data or {}).get(self._register)


class MedolePipeTemperatureSensor(MedoleBaseSensor):
    """Representation of a Medole Pipe Temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: MedoleDataCoordinator, name: str) -> None:
        super().__init__(coordinator, name, "pipe_temperature")
        self._attr_name = "Pipe Temperature"

    @property
    def native_value(self) -> float | None:
        raw = (self.coordinator.data or {}).get(REG_PIPE_TEMPERATURE)
        return raw / 10.0 if raw is not None else None


class MedoleFanOperationHoursSensor(MedoleBaseSensor):
    """Representation of a Medole Fan Operation Hours sensor."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfTime.HOURS

    def __init__(self, coordinator: MedoleDataCoordinator, name: str) -> None:
        super().__init__(coordinator, name, "fan_operation_hours")
        self._attr_name = "Fan Operation Hours"

    @property
    def native_value(self) -> int | None:
        return (self.coordinator.data or {}).get(REG_FAN_OPERATION_HOURS)


class MedoleFanAlarmHoursSensor(MedoleBaseSensor):
    """Representation of a Medole Fan Alarm Hours sensor."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.HOURS

    def __init__(self, coordinator: MedoleDataCoordinator, name: str) -> None:
        super().__init__(coordinator, name, "fan_alarm_hours")
        self._attr_name = "Fan Alarm Hours"

    @property
    def native_value(self) -> int | None:
        return (self.coordinator.data or {}).get(REG_FAN_ALARM_HOURS)


class MedoleStatusSensor(MedoleBaseSensor):
    """Representation of a Medole Status sensor."""

    def __init__(self, coordinator: MedoleDataCoordinator, name: str) -> None:
        super().__init__(coordinator, name, "status")
        self._attr_name = "Status"

    def _status_value(self) -> int | None:
        return (self.coordinator.data or {}).get(REG_OPERATION_STATUS)

    def _mode(self, register: int) -> bool:
        return (self.coordinator.data or {}).get(register) == 1

    @property
    def extra_state_attributes(self) -> dict:
        status = self._status_value()
        if status is None:
            return {}

        lo_byte = status & 0xFF
        hi_byte = (status >> 8) & 0xFF
        return {
            "compressor_on": bool(lo_byte & STATUS_COMPRESSOR_ON),
            "fan_on": bool(lo_byte & STATUS_FAN_ON),
            "dehumidify_mode": self._mode(REG_DEHUMIDIFY_MODE),
            "air_purification_mode": self._mode(REG_PURIFY_MODE),
            "pipe_temp_error": bool(lo_byte & STATUS_PIPE_TEMP_ERROR),
            "humidity_sensor_error": bool(
                lo_byte & STATUS_HUMIDITY_SENSOR_ERROR
            ),
            "room_temp_error": bool(lo_byte & STATUS_ROOM_TEMP_ERROR),
            "water_full_error": bool(lo_byte & STATUS_WATER_FULL_ERROR),
            "high_pressure_error": bool(
                hi_byte & (STATUS_HIGH_PRESSURE_ERROR >> 8)
            ),
            "low_pressure_error": bool(
                hi_byte & (STATUS_LOW_PRESSURE_ERROR >> 8)
            ),
        }

    @property
    def native_value(self) -> str | None:
        status = self._status_value()
        if status is None:
            return None

        lo_byte = status & 0xFF
        hi_byte = (status >> 8) & 0xFF

        errors = []
        if lo_byte & STATUS_PIPE_TEMP_ERROR:
            errors.append("pipe_temp_error")
        if lo_byte & STATUS_HUMIDITY_SENSOR_ERROR:
            errors.append("humidity_sensor_error")
        if lo_byte & STATUS_ROOM_TEMP_ERROR:
            errors.append("room_temp_error")
        if lo_byte & STATUS_WATER_FULL_ERROR:
            errors.append("water_full_error")
        if hi_byte & (STATUS_HIGH_PRESSURE_ERROR >> 8):
            errors.append("high_pressure_error")
        if hi_byte & (STATUS_LOW_PRESSURE_ERROR >> 8):
            errors.append("low_pressure_error")

        if errors:
            return "Error: " + ", ".join(errors)
        if lo_byte & STATUS_COMPRESSOR_ON:
            return "Dehumidifying"
        if lo_byte & STATUS_FAN_ON:
            if self._mode(REG_PURIFY_MODE) and not self._mode(
                REG_DEHUMIDIFY_MODE
            ):
                return "Air Purification"
            return "Fan Only"
        return "Idle"
