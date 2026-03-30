# JBD BMS Monitor

Linux dashboard for JBD/Jiabaida LiFePO4 Battery Management Systems.

## Features

- Connects via USB/serial (CH342 adapter) or Bluetooth BLE (Xiaoxiang module)
- Real-time display: pack voltage, current, SOC, cell voltages, temperature, FET status, protection flags
- Configurable alerts with system tray notifications
- SQLite logging with history charts and CSV export
- Built-in simulator for testing without hardware

## Install

```bash
pip install jbd-bms-dashboard
```

Or from source:

```bash
git clone https://github.com/dpaschal/jbd-bms-dashboard
cd jbd-bms-dashboard
pip install -e ".[dev]"
```

**System dependency (for simulator):**
```bash
sudo pacman -S socat    # Arch
sudo apt install socat  # Debian/Ubuntu
```

## Usage

```bash
# Launch dashboard
jbd-bms

# Or run from source
python main.py
```

Select your port in the toolbar dropdown and click **Connect**.

For BLE: click **BLE Scan…**, select your device, then click **Connect**.

## Simulator

Test the dashboard without hardware:

```bash
# Terminal 1 — start simulator
jbd-bms-sim --scenario normal --cells 16

# Terminal 2 — start dashboard, connect to /tmp/bms-app
jbd-bms
```

Available scenarios:

| Scenario | What it tests |
|---|---|
| `normal` | Steady discharge, minor voltage noise |
| `cell-drift` | One cell slowly drifting below pack |
| `overvoltage` | Overvoltage protection flag |
| `overtemp` | Temperature rising past threshold |
| `disconnect` | Simulates cable disconnect |

## Hardware wiring

The JBD BMS communicates via UART at 9600 baud. Most units ship with or sell a CH342 USB-to-serial adapter cable. Plug it in — Linux usually assigns `/dev/ttyUSB0` or `/dev/ttyACM0`.

For Bluetooth: the Xiaoxiang BLE module pairs automatically. Use **BLE Scan** in the app.

Protocol documentation: [JBD RS485/UART/BLE Protocol PDF](https://cdn.shopifycdn.net/s/files/1/0606/5199/5298/files/JDB_RS485-RS232-UART-Bluetooth-Communication_Protocol.pdf)

## License

MIT
