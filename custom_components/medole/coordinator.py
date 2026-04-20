"""DataUpdateCoordinator for the Medole Dehumidifier integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    REG_DEHUMIDIFY_MODE,
    REG_FAN_ALARM_HOURS,
    REG_FAN_OPERATION_HOURS,
    REG_FAN_SPEED,
    REG_HUMIDITY_1,
    REG_HUMIDITY_2,
    REG_HUMIDITY_SETPOINT,
    REG_OPERATION_STATUS,
    REG_PIPE_TEMPERATURE,
    REG_POWER,
    REG_PURIFY_MODE,
    REG_TEMPERATURE_1,
    REG_TEMPERATURE_2,
)
from .modbus import MedoleModbusClient

_LOGGER = logging.getLogger(__name__)

# The complete set of registers any platform entity currently reads.
# Polled once per cycle in a single coordinator refresh — previously each
# of the 8 entities issued its own independent read loop at 5 s intervals.
REGISTERS_TO_POLL: tuple[int, ...] = (
    REG_POWER,
    REG_OPERATION_STATUS,
    REG_HUMIDITY_SETPOINT,
    REG_DEHUMIDIFY_MODE,
    REG_PURIFY_MODE,
    REG_HUMIDITY_1,
    REG_HUMIDITY_2,
    REG_TEMPERATURE_1,
    REG_TEMPERATURE_2,
    REG_PIPE_TEMPERATURE,
    REG_FAN_OPERATION_HOURS,
    REG_FAN_ALARM_HOURS,
    REG_FAN_SPEED,
)


class MedoleDataCoordinator(DataUpdateCoordinator[dict[int, int]]):
    """Polls all Medole registers in one cycle and fans out to entities."""

    def __init__(
        self, hass: HomeAssistant, client: MedoleModbusClient, name: str
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({name})",
            update_interval=timedelta(seconds=5),
        )
        self.client = client

    async def _async_update_data(self) -> dict[int, int]:
        """Read every polled register. Raises UpdateFailed on any failure."""
        data: dict[int, int] = {}
        for register in REGISTERS_TO_POLL:
            result = await self.client.async_read_register(register)
            if result is None:
                raise UpdateFailed(
                    f"Failed to read register 0x{register:04X} — device "
                    "unreachable or Modbus error"
                )
            data[register] = result.registers[0]
        return data
