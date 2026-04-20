"""Humidifier platform for Medole Dehumidifier integration."""

import logging

from homeassistant.components.humidifier import (
    HumidifierAction,
    HumidifierDeviceClass,
    HumidifierEntity,
    HumidifierEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONTINUOUS_DEHUMIDIFICATION,
    DOMAIN,
    MAX_HUMIDITY,
    MIN_HUMIDITY,
    REG_DEHUMIDIFY_MODE,
    REG_HUMIDITY_1,
    REG_HUMIDITY_SETPOINT,
    REG_OPERATION_STATUS,
    REG_POWER,
    REG_PURIFY_MODE,
    STATUS_COMPRESSOR_ON,
    STATUS_FAN_ON,
)
from .coordinator import MedoleDataCoordinator

_LOGGER = logging.getLogger(__name__)

PRESET_MODE_DEHUMIDIFY = "Dehumidify"
PRESET_MODE_AIR_PURIFICATION = "Air Purification"
PRESET_MODES = [PRESET_MODE_DEHUMIDIFY, PRESET_MODE_AIR_PURIFICATION]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Medole Dehumidifier humidifier platform."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = data["coordinator"]
    name = data["config"][CONF_NAME]

    async_add_entities([MedoleDehumidifierHumidifier(coordinator, name)])


class MedoleDehumidifierHumidifier(
    CoordinatorEntity[MedoleDataCoordinator], HumidifierEntity
):
    """Representation of a Medole Dehumidifier humidifier device."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = HumidifierEntityFeature.MODES
    _attr_device_class = HumidifierDeviceClass.DEHUMIDIFIER
    _attr_available_modes = PRESET_MODES
    _attr_min_humidity = MIN_HUMIDITY
    _attr_max_humidity = MAX_HUMIDITY

    def __init__(self, coordinator: MedoleDataCoordinator, name: str) -> None:
        """Initialize the humidifier device."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{name}_humidifier"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": name,
            "manufacturer": "Medole",
            "model": "IN-D17",
        }
        # Remembered so async_turn_on can restore the last picked preset.
        self._current_preset = PRESET_MODE_DEHUMIDIFY
        self._update_from_coordinator()

    @property
    def _client(self):
        """Modbus client used for writes — reads go through the coordinator."""
        return self.coordinator.client

    @callback
    def _handle_coordinator_update(self) -> None:
        """Pull fresh state from the coordinator and schedule an HA update."""
        self._update_from_coordinator()
        super()._handle_coordinator_update()

    def _update_from_coordinator(self) -> None:
        """Derive entity attributes from the coordinator's latest snapshot."""
        data = self.coordinator.data or {}

        power = data.get(REG_POWER)
        self._attr_is_on = power == 1

        status = data.get(REG_OPERATION_STATUS)
        if status is None:
            self._attr_action = None
        elif not self._attr_is_on:
            self._attr_action = HumidifierAction.OFF
        elif status & STATUS_COMPRESSOR_ON:
            self._attr_action = HumidifierAction.DRYING
        elif status & STATUS_FAN_ON:
            self._attr_action = HumidifierAction.IDLE
        else:
            self._attr_action = HumidifierAction.IDLE

        setpoint = data.get(REG_HUMIDITY_SETPOINT)
        if setpoint is not None:
            self._attr_target_humidity = (
                MIN_HUMIDITY
                if setpoint == CONTINUOUS_DEHUMIDIFICATION
                else setpoint
            )

        dehumidify_on = data.get(REG_DEHUMIDIFY_MODE) == 1
        purify_on = data.get(REG_PURIFY_MODE) == 1
        if dehumidify_on:
            self._current_preset = PRESET_MODE_DEHUMIDIFY
            self._attr_mode = PRESET_MODE_DEHUMIDIFY
        elif purify_on:
            self._current_preset = PRESET_MODE_AIR_PURIFICATION
            self._attr_mode = PRESET_MODE_AIR_PURIFICATION
        else:
            self._attr_mode = PRESET_MODE_DEHUMIDIFY

        humidity = data.get(REG_HUMIDITY_1)
        if humidity is not None:
            self._attr_current_humidity = humidity

    async def async_set_mode(self, mode: str) -> None:
        """Set new mode."""
        if mode == PRESET_MODE_AIR_PURIFICATION:
            await self._client.async_write_register(REG_DEHUMIDIFY_MODE, 0)
            success = await self._client.async_write_register(
                REG_PURIFY_MODE, 1
            )
            if success:
                self._current_preset = PRESET_MODE_AIR_PURIFICATION
        elif mode == PRESET_MODE_DEHUMIDIFY:
            await self._client.async_write_register(REG_PURIFY_MODE, 1)
            success = await self._client.async_write_register(
                REG_DEHUMIDIFY_MODE, 1
            )
            if success:
                self._current_preset = PRESET_MODE_DEHUMIDIFY
        else:
            _LOGGER.error("Unknown mode: %s", mode)
            return

        if not success:
            _LOGGER.error("Failed to set mode to %s", mode)
        await self.coordinator.async_request_refresh()

    async def async_set_humidity(self, humidity: int) -> None:
        """Set new target humidity."""
        humidity = max(MIN_HUMIDITY, min(MAX_HUMIDITY, humidity))

        if not await self._client.async_write_register(
            REG_HUMIDITY_SETPOINT, humidity
        ):
            _LOGGER.error("Failed to set humidity to %s", humidity)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the device on and restore the previous preset."""
        if not await self._client.async_write_register(REG_POWER, 1):
            _LOGGER.error("Failed to turn on device")

        if self._current_preset == PRESET_MODE_AIR_PURIFICATION:
            await self._client.async_write_register(REG_DEHUMIDIFY_MODE, 0)
            await self._client.async_write_register(REG_PURIFY_MODE, 1)
        else:
            await self._client.async_write_register(REG_PURIFY_MODE, 1)
            await self._client.async_write_register(REG_DEHUMIDIFY_MODE, 1)

        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the device off."""
        if not await self._client.async_write_register(REG_POWER, 0):
            _LOGGER.error("Failed to turn power off")
        await self.coordinator.async_request_refresh()
