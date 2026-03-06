"""Select platform for Medole Dehumidifier integration - Fan Speed control."""

import logging
from datetime import timedelta

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    FAN_SPEED_HIGH,
    FAN_SPEED_LOW,
    FAN_SPEED_MEDIUM,
    REG_FAN_SPEED,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)

FAN_SPEED_OPTIONS = ["low", "medium", "high"]

FAN_SPEED_MAP = {
    "low": FAN_SPEED_LOW,
    "medium": FAN_SPEED_MEDIUM,
    "high": FAN_SPEED_HIGH,
}
FAN_SPEED_REVERSE_MAP = {v: k for k, v in FAN_SPEED_MAP.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Medole Dehumidifier select platform."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    config = data["config"]
    client = data["client"]
    name = config[CONF_NAME]

    async_add_entities([MedoleFanSpeedSelect(hass, name, client)], True)


class MedoleFanSpeedSelect(SelectEntity):
    """Fan speed selector for Medole Dehumidifier."""

    _attr_has_entity_name = True
    _attr_translation_key = "fan_speed"
    _attr_options = FAN_SPEED_OPTIONS
    _attr_current_option = None

    def __init__(self, hass, name, client):
        """Initialize the fan speed select entity."""
        self.hass = hass
        self._client = client
        self._attr_unique_id = f"{name}_fan_speed"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{name}_humidifier")},
            "name": name,
            "manufacturer": "Medole",
            "model": "IN-D17",
        }

    async def async_update(self) -> None:
        """Read current fan speed from device."""
        result = await self._client.async_read_register(REG_FAN_SPEED)
        if result:
            speed_value = result.registers[0]
            self._attr_current_option = FAN_SPEED_REVERSE_MAP.get(speed_value)
            self._attr_available = True
        else:
            _LOGGER.error("Failed to read fan speed")
            self._attr_available = False

    async def async_select_option(self, option: str) -> None:
        """Write selected fan speed to device."""
        speed_value = FAN_SPEED_MAP.get(option, FAN_SPEED_HIGH)
        success = await self._client.async_write_register(
            REG_FAN_SPEED, speed_value
        )
        if success:
            self._attr_current_option = option
            self._attr_available = True
        else:
            _LOGGER.error("Failed to set fan speed to %s", option)
            self._attr_available = False
        self.async_write_ha_state()
