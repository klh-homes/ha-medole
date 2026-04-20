"""Select platform for Medole Dehumidifier integration - Fan Speed control."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    FAN_SPEED_HIGH,
    FAN_SPEED_LOW,
    FAN_SPEED_MEDIUM,
    REG_FAN_SPEED,
)
from .coordinator import MedoleDataCoordinator

_LOGGER = logging.getLogger(__name__)

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
    coordinator = data["coordinator"]
    name = data["config"][CONF_NAME]

    async_add_entities([MedoleFanSpeedSelect(coordinator, name)])


class MedoleFanSpeedSelect(
    CoordinatorEntity[MedoleDataCoordinator], SelectEntity
):
    """Fan speed selector for Medole Dehumidifier."""

    _attr_has_entity_name = True
    _attr_translation_key = "fan_speed"
    _attr_options = FAN_SPEED_OPTIONS

    def __init__(self, coordinator: MedoleDataCoordinator, name: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{name}_fan_speed"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{name}_humidifier")},
            "name": name,
            "manufacturer": "Medole",
            "model": "IN-D17",
        }

    @property
    def current_option(self) -> str | None:
        raw = (self.coordinator.data or {}).get(REG_FAN_SPEED)
        return FAN_SPEED_REVERSE_MAP.get(raw) if raw is not None else None

    async def async_select_option(self, option: str) -> None:
        """Write selected fan speed to device."""
        speed_value = FAN_SPEED_MAP.get(option, FAN_SPEED_HIGH)
        success = await self.coordinator.client.async_write_register(
            REG_FAN_SPEED, speed_value
        )
        if not success:
            _LOGGER.error("Failed to set fan speed to %s", option)
        await self.coordinator.async_request_refresh()
