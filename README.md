# Medole Dehumidifier (米多力除溼機) Integration for Home Assistant

This is a custom component for Home Assistant that integrates Medole Dehumidifier devices via Modbus (serial or TCP). You need to connect a RS485 to Ethernet/Wi-Fi converter to the RS485 port of the Medole Dehumidifier.

> **Fork notice.** This repository is a maintenance fork of [aitjcize/ha-medole](https://github.com/aitjcize/ha-medole). See [Changes from upstream](#changes-from-upstream) for what differs.

## Features

- Control dehumidifier operation (on/off)
- Set target humidity
- Control fan speed
- Monitor temperature and humidity sensors
- Monitor device status and errors

## Changes from upstream

This fork diverges from [aitjcize/ha-medole](https://github.com/aitjcize/ha-medole) in the following ways. Changes may or may not eventually be contributed back upstream.

- **Non-blocking Modbus connect.** `MedoleModbusClient._ensure_connection` used to call `pymodbus`'s blocking `client.connect()` synchronously on the event loop. When the physical device fell off the network, every polling cycle froze Home Assistant for the full TCP timeout (~3 s) and cascaded into MQTT / Supervisor / addon timeouts across the whole instance. The client now dispatches the connect via `hass.async_add_executor_job` and the TCP timeout is lowered from 3 s to 1 s.
- **Single DataUpdateCoordinator.** The eight entities previously each ran their own 5-second polling loop, issuing ~6 independent Modbus reads per entity per cycle. A new `MedoleDataCoordinator` polls the full register set once per cycle and fans the snapshot out to `CoordinatorEntity` subclasses, so entities also share availability / `UpdateFailed` handling for free.
- **Pytest test suite.** `tests/` contains a pytest + pytest-asyncio suite that runs against a live mock Modbus server (the repo's existing `mock-server/`) and exercises the modbus client, coordinator, and entity state derivation. Includes a regression test that specifically catches the event-loop-freeze bug above. Runs via `make test`.
- **HACS metadata.** `hacs.json` declares a minimum HA version and enables `render_readme`. `manifest.json` drops the unused `dependencies: ["modbus"]` declaration, bumps the `pymodbus` requirement floor to `3.11.2`, and points `codeowners` / `documentation` / `issue_tracker` at this fork.
- **CI on Python 3.14.** GitHub Actions workflow runs on Python 3.14 to match the HA 2026.3+ runtime (HA 2026.3.x requires `Python >= 3.14.2`).

## Installation

### HACS (recommended)

1. In HACS, open the three-dot menu → _Custom repositories_, paste this repo URL, set category to _Integration_, and add it.
2. Install "Medole Dehumidifier" from HACS.
3. Restart Home Assistant.
4. _Settings → Devices & Services → Add Integration → Medole Dehumidifier_.

### Manual

1. Copy the `custom_components/medole` directory to your Home Assistant `/config/custom_components/` directory.
2. Restart Home Assistant.
3. _Settings → Devices & Services → Add Integration → Medole Dehumidifier_.

## Configuration

The integration can be configured through the Home Assistant UI. You'll need to provide:

- Name for the device
- Connection type (Serial or TCP)
- For Serial: Port, Slave ID, and optionally baudrate, bytesize, parity, and stopbits
- For TCP: Host, Port, and Slave ID

## Development

Requires Python 3.14 (matching the Home Assistant runtime version this integration targets). Create a virtual environment and install dev dependencies:

```bash
make setup-venv
source .venv/bin/activate
```

Makefile targets:

```bash
# Run linters
make lint

# Run the pytest suite + mock server smoke test
make test

# Run just the pytest suite
make test-pytest

# Format code
make format

# Check formatting without making changes
make check

# Clean up cache files
make clean
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
