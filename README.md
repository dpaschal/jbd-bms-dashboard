# JBD BMS Monitor

<p align="center">
  <a href="https://buymeacoffee.com/dpaschal">
    <img src="https://img.shields.io/badge/❤️🎆_THANKS!_🎆❤️-Support_This_Project-ff0000?style=for-the-badge" alt="Thanks!" height="40">
  </a>
</p>

<p align="center">
  <b>☕ Buy me Claude Code credits or support a project! ☕</b>
</p>
<p align="center">
  <i>Every donation keeps the code flowing — these tools are built with your support.</i>
</p>

<p align="center">
  <a href="https://buymeacoffee.com/dpaschal">
    <img src="https://cdn.buymeacoffee.com/buttons/v2/default-red.png" alt="Buy Me A Coffee" height="50">
  </a>
</p>

---

Linux dashboard for JBD/Jiabaida LiFePO4 Battery Management Systems.

## Features

- Connects via USB/serial (CH342 adapter) or Bluetooth BLE (Xiaoxiang module)
- Real-time display: pack voltage, current, SOC, cell voltages, temperature, FET status, protection flags
- **Separate charge (in) and discharge (out) current display** with power calculation in watts
- **Up to 4 temperature sensors** with color-coded alerts
- **Cell delta (Δ) monitoring** — green (< 10mV), yellow (< 20mV), red (> 20mV)
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

## Tested hardware

| BMS | Cells | Capacity | Connection | Status |
|-----|-------|----------|------------|--------|
| KX4GG (JBD) | 4S LiFePO4 | 302Ah | BLE (Xiaoxiang) | Verified — all data fields |

Verified against the **XiaoxiangBMS Android app (v2.0.6)** — pack voltage, current, SOC, cell voltages, temperature sensors, and protection flags all match.

## Known issues & fixes

### BLE frame reassembly (fixed 2026-04-14)

Early versions used a byte-search for `0x77` (end-of-frame marker) to detect complete BLE frames. This worked for small responses like cell voltages (register `0x04`, ~13 bytes) but failed on the larger BasicInfo response (register `0x03`, 36+ bytes) because `0x77` can appear as a data byte within the payload (voltage values, capacity, temperature, etc.), causing premature frame termination.

**Symptom:** Cell voltages display correctly but pack voltage, current, SOC, temperature, FET status, and protection flags all show `--`.

**Fix:** Frame boundaries are now determined using the protocol's length field at byte offset 3, which gives the exact payload size. Total frame size = `4 + payload_length + 3` bytes. The end byte `0x77` is verified after extraction but no longer used for boundary detection.

## License

MIT
