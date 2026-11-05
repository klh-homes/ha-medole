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
    REG_HUMIDITY_SETPOINT,
    REG_OPERATION_STATUS,
    REG_PIPE_TEMPERATURE,
    REG_POWER,
    REG_PURIFY_MODE,
    REG_TEMPERATURE_1,
)
from .modbus import MedoleModbusClient

_LOGGER = logging.getLogger(__name__)

# Read first each cycle. A failed probe means the device is unavailable; a
# failure from any other register is isolated to the entity that consumes it.
_PROBE_REGISTER = REG_OPERATION_STATUS

# The complete set of registers any platform entity currently reads. Polled
# once per cycle in a single coordinator refresh.
REGISTERS_TO_POLL: tuple[int, ...] = (
    REG_OPERATION_STATUS,
    REG_POWER,
    REG_HUMIDITY_SETPOINT,
    REG_DEHUMIDIFY_MODE,
    REG_PURIFY_MODE,
    REG_HUMIDITY_1,
    REG_TEMPERATURE_1,
    REG_PIPE_TEMPERATURE,
    REG_FAN_OPERATION_HOURS,
    REG_FAN_ALARM_HOURS,
    REG_FAN_SPEED,
)


class MedoleDataCoordinator(DataUpdateCoordinator[dict[int, int | None]]):
    """Poll all Medole registers in one cycle and fan out to entities."""

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

    async def _async_update_data(self) -> dict[int, int | None]:
        """Read every register and fail only when the probe is unreadable."""
        probe = await self.client.async_read_register(_PROBE_REGISTER)
        if probe is None:
            raise UpdateFailed(
                "Failed to read operation status — device unreachable or "
                "Modbus error"
            )

        data: dict[int, int | None] = {_PROBE_REGISTER: probe.registers[0]}
        for register in REGISTERS_TO_POLL:
            if register == _PROBE_REGISTER:
                continue
            result = await self.client.async_read_register(register)
            data[register] = result.registers[0] if result is not None else None
        return data
