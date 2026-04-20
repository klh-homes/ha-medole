"""Tests for entity state derivation against a fake coordinator."""
from unittest.mock import MagicMock

import pytest
from homeassistant.components.humidifier import HumidifierAction

from custom_components.medole.const import (
    FAN_SPEED_HIGH,
    FAN_SPEED_MEDIUM,
    REG_DEHUMIDIFY_MODE,
    REG_FAN_SPEED,
    REG_HUMIDITY_1,
    REG_HUMIDITY_SETPOINT,
    REG_OPERATION_STATUS,
    REG_POWER,
    REG_PURIFY_MODE,
    REG_TEMPERATURE_1,
    STATUS_COMPRESSOR_ON,
    STATUS_FAN_ON,
    STATUS_WATER_FULL_ERROR,
)
from custom_components.medole.humidifier import (
    PRESET_MODE_DEHUMIDIFY,
    MedoleDehumidifierHumidifier,
)
from custom_components.medole.select import MedoleFanSpeedSelect
from custom_components.medole.sensor import (
    MedoleStatusSensor,
    MedoleTemperatureSensor,
)


def _fake_coordinator(data: dict, client=None) -> MagicMock:
    """Build a MagicMock that quacks like MedoleDataCoordinator for tests."""
    coord = MagicMock()
    coord.data = data
    coord.client = client if client is not None else MagicMock()

    async def _refresh():
        return None

    coord.async_request_refresh = _refresh
    return coord


async def test_humidifier_state_from_registers():
    coordinator = _fake_coordinator({
        REG_POWER: 1,
        REG_OPERATION_STATUS: STATUS_COMPRESSOR_ON | STATUS_FAN_ON,
        REG_HUMIDITY_SETPOINT: 50,
        REG_DEHUMIDIFY_MODE: 1,
        REG_PURIFY_MODE: 1,
        REG_HUMIDITY_1: 60,
    })
    entity = MedoleDehumidifierHumidifier(coordinator, "unit")

    assert entity._attr_is_on is True
    assert entity._attr_mode == PRESET_MODE_DEHUMIDIFY
    assert entity._attr_target_humidity == 50
    assert entity._attr_current_humidity == 60
    assert entity._attr_action == HumidifierAction.DRYING


async def test_status_sensor_bitmask_decoding():
    coordinator = _fake_coordinator({
        REG_OPERATION_STATUS: (
            STATUS_COMPRESSOR_ON | STATUS_FAN_ON | STATUS_WATER_FULL_ERROR
        ),
        REG_DEHUMIDIFY_MODE: 1,
        REG_PURIFY_MODE: 0,
    })
    entity = MedoleStatusSensor(coordinator, "unit")

    assert "water_full_error" in entity.native_value
    attrs = entity.extra_state_attributes
    assert attrs["compressor_on"] is True
    assert attrs["fan_on"] is True
    assert attrs["dehumidify_mode"] is True
    assert attrs["air_purification_mode"] is False
    assert attrs["water_full_error"] is True


async def test_temperature_sensor_decoding():
    """Temperature register packs hi-byte=decimal, lo-byte=integer."""
    # 25.5°C: integer=25 (0x19), decimal=5 (0x05) → 0x0519
    coordinator = _fake_coordinator({REG_TEMPERATURE_1: 0x0519})
    entity = MedoleTemperatureSensor(coordinator, "unit", 1)

    assert entity.native_value == pytest.approx(25.5)


async def test_fan_speed_select_read_and_write(fake_client):
    """Fan speed select reads current value and round-trips a write."""
    coordinator = _fake_coordinator(
        {REG_FAN_SPEED: FAN_SPEED_MEDIUM}, client=fake_client
    )
    entity = MedoleFanSpeedSelect(coordinator, "unit")

    assert entity.current_option == "medium"

    await entity.async_select_option("high")
    assert (REG_FAN_SPEED, FAN_SPEED_HIGH) in fake_client.writes
