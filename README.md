# Medole Dehumidifier (米多力除溼機) Integration for Home Assistant

This is a custom component for Home Assistant that integrates Medole Dehumidifier devices via Modbus (serial or TCP). You need to connect a RS485 to Ethernet/Wi-Fi converter to the RS485 port of the Medole Dehumidifier.

## Features

- Control dehumidifier operation (on/off)
- Set target humidity
- Control fan speed
- Monitor temperature and humidity sensors
- Monitor device status and errors

## Installation

1. Copy the `custom_components/medole_dehumidifier` directory to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration through the Home Assistant UI (Configuration > Integrations > Add Integration).

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
