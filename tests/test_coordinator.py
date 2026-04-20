"""Tests for MedoleDataCoordinator._async_update_data."""
import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.medole.const import REG_HUMIDITY_1, REG_POWER
from custom_components.medole.coordinator import (
    REGISTERS_TO_POLL,
    MedoleDataCoordinator,
)


class _CapturingCoordinator(MedoleDataCoordinator):
    """Bypasses DataUpdateCoordinator.__init__ so we can unit-test the poll loop.

    The real __init__ wants a fully-wired HomeAssistant (event loop, bus, …).
    For this unit test we only need self.client, so we skip super().__init__.
    """

    def __init__(self, client):
        self.client = client


async def test_coordinator_reads_every_polled_register(fake_client):
    # Seed every register the coordinator is expected to read.
    for i, reg in enumerate(REGISTERS_TO_POLL):
        fake_client.values[reg] = i + 1

    coordinator = _CapturingCoordinator(fake_client)
    data = await coordinator._async_update_data()

    assert set(data.keys()) == set(REGISTERS_TO_POLL)
    assert data[REG_POWER] == REGISTERS_TO_POLL.index(REG_POWER) + 1
    assert data[REG_HUMIDITY_1] == (
        REGISTERS_TO_POLL.index(REG_HUMIDITY_1) + 1
    )


async def test_coordinator_raises_update_failed_when_device_unreachable(
    fake_client,
):
    # fake_client.values is empty → async_read_register returns None for every
    # register, which is how the client signals "device unreachable".
    coordinator = _CapturingCoordinator(fake_client)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
