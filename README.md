# Bluetooth Sensor Monitor

This repository contains a simple application that connects to a BLE sensor
(LT_3917) and displays temperature and humidity data in a PySide6 interface.
It uses `bleak` for the Bluetooth communication and `qasync` to integrate the
Qt event loop with `asyncio`.

## Requirements

- Python 3.12+
- PySide6
- bleak
- qasync

Install the dependencies with:

```bash
pip install PySide6 bleak qasync
```

## Running

Launch the monitor with:

```bash
python sensor_app.py
```

The application scans for the device `LT_3917` and automatically connects when
found. Received data are logged to `~/Documentos/sensor_log.csv` along with a
timestamp.
