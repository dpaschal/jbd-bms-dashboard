# JBD BMS Dashboard — Design Spec
**Date:** 2026-03-29
**Status:** Approved

## Overview

A Linux desktop dashboard for monitoring Jiabaida (JBD) LiFePO4 battery management systems. Connects via USB/serial or Bluetooth (BLE), displays real-time pack and cell data, logs history to SQLite, and alerts on configurable thresholds. Includes a BMS simulator for testing without hardware.

## Tech Stack

- **Language:** Python 3.11+
- **UI:** PyQt6 + pyqtgraph (real-time plots)
- **BLE:** bleak (asyncio, runs in dedicated thread)
- **Serial:** pyserial (runs in QThread)
- **Storage:** SQLite via Python stdlib `sqlite3`
- **Packaging:** pyproject.toml (pip-installable)
- **Protocol:** JBD RS485/UART/BLE binary protocol (publicly documented)

## Package Structure

```
jbd-bms-dashboard/
├── bms_monitor/
│   ├── protocol/
│   │   ├── frames.py       # dataclasses: BasicInfo, CellVoltages, BMSInfo
│   │   └── parser.py       # encode/decode JBD binary frames
│   ├── transport/
│   │   ├── base.py         # abstract Transport interface
│   │   ├── serial.py       # SerialTransport — pyserial in QThread
│   │   └── ble.py          # BLETransport — bleak in asyncio thread
│   ├── simulator/
│   │   └── simulator.py    # virtual BMS over socat pty pair
│   ├── storage/
│   │   └── db.py           # SQLite schema, write snapshot, query history
│   ├── alerts/
│   │   └── checker.py      # threshold monitor, emits Qt signals
│   └── ui/
│       ├── main_window.py
│       ├── widgets/
│       │   ├── overview.py      # stats row + live pyqtgraph chart
│       │   ├── cells.py         # per-cell voltage bar chart
│       │   ├── history.py       # logged session chart + CSV export
│       │   └── settings.py      # port picker, BLE scanner, thresholds
│       └── alerts_dialog.py
├── main.py                 # app entry point
├── simulator_main.py       # run simulator standalone
├── pyproject.toml
└── README.md
```

## Architecture

### Threading Model
- **Main thread:** PyQt6 event loop, UI rendering, protocol parsing, alert checking
- **QThread:** `SerialTransport` — blocking serial reads, emits `frame_received(bytes)` signal
- **asyncio thread:** `BLETransport` — bleak event loop, bridges to Qt via `call_soon_threadsafe`
- Protocol parsing and alert checking run on the main thread (frames are small, <100 bytes)

### Transport Abstraction
Both transports implement the same interface:
```python
class Transport:
    def connect(self, target: str) -> None: ...
    def disconnect(self) -> None: ...
    # emits Qt signal: frame_received(bytes)
```
The rest of the app never knows whether it's talking to serial or BLE.

## Data Flow

```
BMS Hardware / Simulator
        │  JBD binary frames
        ▼
  Transport (QThread / asyncio thread)
        │  Qt signal: frame_received(bytes)
        ▼
  Protocol Parser  →  BasicInfo | CellVoltages | BMSInfo
        │
  ┌─────┴──────┐
  │            │
  UI Widgets   AlertChecker ──► Qt signal ──► system tray + UI banner
  (live)              │
                 SQLite DB (snapshot every N seconds)
                      │
                 HistoryWidget (query + plot on demand)
```

## UI Layout — Single Window (~900×650px)

1. **Toolbar:** port dropdown, BLE scan button, connect/disconnect, poll interval selector, settings button
2. **Stats row (6 tiles):** Pack Voltage, Current, SOC%, Remaining Ah, Temperature, Cycle Count
3. **Middle row:**
   - Left (3/4 width): per-cell voltage bar chart, color-coded (red = out of range), shows max cell delta
   - Right (1/4 width): FET status (charge/discharge ON/OFF), protection flags list
4. **Bottom panel:** tabbed Live chart / History chart (pyqtgraph, voltage + current overlay), log toggle
5. **Status bar:** connection status, last update time, active log filename

## Protocol

JBD uses a simple request/response binary protocol over all transports:
- **Register 0x03:** BasicInfo — pack voltage, current, SOC, capacity, cycles, temps, FET status, protection flags
- **Register 0x04:** CellVoltages — individual cell voltages (up to 32 cells)
- **Register 0x05:** BMSInfo — hardware version, BMS name
- App polls 0x03 + 0x04 on a configurable interval (default 1s)

## Storage

**SQLite schema:**
```sql
CREATE TABLE snapshots (
    id INTEGER PRIMARY KEY,
    ts REAL NOT NULL,               -- Unix timestamp
    pack_voltage REAL,
    current REAL,
    soc INTEGER,
    remaining_ah REAL,
    temp1 REAL,
    temp2 REAL,
    cycles INTEGER,
    cell_voltages TEXT,             -- JSON array
    charge_fet INTEGER,
    discharge_fet INTEGER,
    protection_flags TEXT           -- JSON object
);
```

One DB file per day, named `bms_YYYY-MM-DD.db`. History tab lets user select any DB file for review. CSV export button on the History tab.

## Alerts

Thresholds stored in `settings.json`:
```json
{
  "cell_undervolt": 3.0,
  "cell_overvolt": 3.65,
  "pack_undervolt": 44.8,
  "temp_max": 45,
  "current_max": 100
}
```
- Rate-limited: one alert per condition per 60 seconds
- Delivery: Qt system tray notification + non-blocking in-app banner
- All thresholds configurable via Settings panel

## Simulator

`simulator_main.py` creates a virtual serial port pair via `socat`:
```
/tmp/bms-sim  ←→  /tmp/bms-app
```
Responds to JBD poll requests with realistic generated data. Point the app at `/tmp/bms-app` to use it.

**Scenarios** (`--scenario` flag):
| Scenario | Behavior |
|---|---|
| `normal` | Steady discharge, minor voltage noise |
| `cell-drift` | One cell slowly diverging from pack |
| `overvoltage` | Triggers overvoltage protection flag |
| `overtemp` | Temperature rising past threshold |
| `disconnect` | Simulates mid-session cable pull |

## Distribution

- `pip install jbd-bms-dashboard` (PyPI)
- Public GitHub repo: `github.com/dpaschal/jbd-bms-dashboard`
- `README.md` covers install, usage, simulator quickstart, and hardware wiring notes
- MIT license
