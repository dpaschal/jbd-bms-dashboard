# JBD BMS Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Linux desktop dashboard for JBD/Jiabaida LiFePO4 BMS with USB/serial and BLE connectivity, real-time display, SQLite logging, configurable alerts, and a built-in simulator.

**Architecture:** PyQt6 app with a QThread-based serial transport and an asyncio-thread-based BLE transport. All I/O runs off the main thread; parsed frames are delivered via Qt signals. The simulator speaks the JBD protocol over a socat virtual serial port pair so the app cannot distinguish it from real hardware.

**Tech Stack:** Python 3.11+, PyQt6 6.6+, pyqtgraph 0.13+, pyserial 3.5+, bleak 0.21+, SQLite (stdlib), pytest 8+, pytest-qt 4.4+

---

## File Map

```
jbd-bms-dashboard/
├── bms_monitor/
│   ├── __init__.py
│   ├── config.py                  # load/save settings.json
│   ├── protocol/
│   │   ├── __init__.py
│   │   ├── frames.py              # dataclasses: BasicInfo, CellVoltages, BMSInfo, ProtectionFlags
│   │   └── parser.py              # encode requests, decode responses
│   ├── transport/
│   │   ├── __init__.py
│   │   ├── base.py                # abstract Transport(QObject) with signals
│   │   ├── serial.py              # SerialTransport — pyserial in QThread
│   │   └── ble.py                 # BLETransport — bleak in asyncio thread
│   ├── simulator/
│   │   ├── __init__.py
│   │   └── simulator.py           # virtual BMS via socat pty pair
│   ├── storage/
│   │   ├── __init__.py
│   │   └── db.py                  # SQLite schema, write_snapshot, query_snapshots, export_csv
│   ├── alerts/
│   │   ├── __init__.py
│   │   └── checker.py             # AlertChecker(QObject) — threshold monitor
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py         # MainWindow — toolbar + layout + signal wiring
│       └── widgets/
│           ├── __init__.py
│           ├── stats_row.py       # 6-tile stats bar
│           ├── cells_widget.py    # per-cell bar chart
│           ├── live_chart.py      # pyqtgraph voltage + current overlay
│           ├── history_widget.py  # query DB, plot, CSV export
│           ├── settings_panel.py  # port picker, BLE scan, thresholds
│           └── alerts_banner.py   # in-app non-blocking alert banner
├── tests/
│   ├── conftest.py
│   ├── protocol/
│   │   ├── test_frames.py
│   │   └── test_parser.py
│   ├── storage/
│   │   └── test_db.py
│   ├── alerts/
│   │   └── test_checker.py
│   └── simulator/
│       └── test_simulator.py
├── main.py
├── simulator_main.py
├── pyproject.toml
├── .gitignore
└── README.md
```

---

## Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `bms_monitor/__init__.py` (and all `__init__.py` files)
- Create: `tests/conftest.py`
- Create: `.gitignore`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "jbd-bms-dashboard"
version = "0.1.0"
description = "Linux dashboard for JBD/Jiabaida LiFePO4 BMS"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.11"
dependencies = [
    "PyQt6>=6.6.0",
    "pyqtgraph>=0.13.4",
    "pyserial>=3.5",
    "bleak>=0.21.1",
]

[project.scripts]
jbd-bms = "main:main"
jbd-bms-sim = "simulator_main:main"

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-qt>=4.4"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create all `__init__.py` files and directory structure**

```bash
mkdir -p bms_monitor/{protocol,transport,simulator,storage,alerts,ui/widgets}
mkdir -p tests/{protocol,storage,alerts,simulator}
touch bms_monitor/__init__.py
touch bms_monitor/{protocol,transport,simulator,storage,alerts}/__init__.py
touch bms_monitor/ui/__init__.py bms_monitor/ui/widgets/__init__.py
touch tests/__init__.py tests/{protocol,storage,alerts,simulator}/__init__.py
```

- [ ] **Step 3: Write `tests/conftest.py`**

```python
import pytest
from PyQt6.QtWidgets import QApplication
import sys

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app
```

- [ ] **Step 4: Write `.gitignore`**

```
__pycache__/
*.pyc
*.egg-info/
dist/
build/
.venv/
*.db
settings.json
/tmp/bms-*
.superpowers/
```

- [ ] **Step 5: Install dev dependencies and verify pytest runs**

```bash
pip install -e ".[dev]"
pytest --collect-only
```
Expected: "no tests ran" with 0 errors.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml bms_monitor/ tests/ .gitignore
git commit -m "feat: project scaffold"
```

---

## Task 2: Protocol frames

**Files:**
- Create: `bms_monitor/protocol/frames.py`
- Create: `tests/protocol/test_frames.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/protocol/test_frames.py
from bms_monitor.protocol.frames import BasicInfo, CellVoltages, BMSInfo, ProtectionFlags

def test_protection_flags_all_clear():
    flags = ProtectionFlags.from_bitmask(0x0000)
    assert flags.cell_overvolt is False
    assert flags.cell_undervolt is False
    assert flags.short_circuit is False

def test_protection_flags_cell_undervolt():
    flags = ProtectionFlags.from_bitmask(0x0002)
    assert flags.cell_undervolt is True
    assert flags.cell_overvolt is False

def test_basic_info_fields():
    info = BasicInfo(
        pack_voltage=51.2, current=12.4, remaining_ah=83.0,
        nominal_ah=100.0, cycles=42, soc=83,
        charge_fet=True, discharge_fet=True,
        cell_count=16, temp_count=2, temps=[25.0, 26.0],
        protection=ProtectionFlags.from_bitmask(0),
        balance_bitmask=0,
    )
    assert info.pack_voltage == 51.2
    assert info.soc == 83
    assert len(info.temps) == 2

def test_cell_voltages():
    cells = CellVoltages(voltages=[3.21] * 16)
    assert len(cells.voltages) == 16
    assert cells.max_voltage == pytest.approx(3.21)
    assert cells.min_voltage == pytest.approx(3.21)
    assert cells.delta == pytest.approx(0.0, abs=1e-6)

def test_cell_voltages_delta():
    cells = CellVoltages(voltages=[3.21, 3.09, 3.21, 3.20])
    assert cells.delta == pytest.approx(0.12, abs=0.001)
    assert cells.min_voltage == pytest.approx(3.09)
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/protocol/test_frames.py -v
```
Expected: ImportError — `frames` module not found.

- [ ] **Step 3: Write `bms_monitor/protocol/frames.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ProtectionFlags:
    cell_overvolt: bool = False
    cell_undervolt: bool = False
    pack_overvolt: bool = False
    pack_undervolt: bool = False
    charge_overcurrent: bool = False
    discharge_overcurrent: bool = False
    short_circuit: bool = False
    ic_error: bool = False
    mos_lock: bool = False

    @classmethod
    def from_bitmask(cls, mask: int) -> ProtectionFlags:
        return cls(
            cell_overvolt=bool(mask & 0x0001),
            cell_undervolt=bool(mask & 0x0002),
            pack_overvolt=bool(mask & 0x0004),
            pack_undervolt=bool(mask & 0x0008),
            charge_overcurrent=bool(mask & 0x0010),
            discharge_overcurrent=bool(mask & 0x0020),
            short_circuit=bool(mask & 0x0040),
            ic_error=bool(mask & 0x0080),
            mos_lock=bool(mask & 0x0100),
        )

    @property
    def any_fault(self) -> bool:
        return any([
            self.cell_overvolt, self.cell_undervolt,
            self.pack_overvolt, self.pack_undervolt,
            self.charge_overcurrent, self.discharge_overcurrent,
            self.short_circuit, self.ic_error, self.mos_lock,
        ])


@dataclass
class BasicInfo:
    pack_voltage: float       # V
    current: float            # A (positive=charge, negative=discharge)
    remaining_ah: float       # Ah
    nominal_ah: float         # Ah
    cycles: int
    soc: int                  # 0–100 %
    charge_fet: bool
    discharge_fet: bool
    cell_count: int
    temp_count: int
    temps: list[float]        # °C
    protection: ProtectionFlags
    balance_bitmask: int


@dataclass
class CellVoltages:
    voltages: list[float]     # V per cell

    @property
    def max_voltage(self) -> float:
        return max(self.voltages)

    @property
    def min_voltage(self) -> float:
        return min(self.voltages)

    @property
    def delta(self) -> float:
        return self.max_voltage - self.min_voltage


@dataclass
class BMSInfo:
    name: str
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/protocol/test_frames.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add bms_monitor/protocol/frames.py tests/protocol/test_frames.py
git commit -m "feat: protocol frames dataclasses"
```

---

## Task 3: Protocol parser

**Files:**
- Create: `bms_monitor/protocol/parser.py`
- Create: `tests/protocol/test_parser.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/protocol/test_parser.py
import struct
import pytest
from bms_monitor.protocol.parser import (
    make_read_request, parse_response, ParseError,
)
from bms_monitor.protocol.frames import BasicInfo, CellVoltages

REG_BASIC = 0x03
REG_CELLS = 0x04
REG_INFO  = 0x05


def _checksum(payload: bytes) -> bytes:
    cs = (~sum(payload) + 1) & 0xFFFF
    return bytes([cs >> 8, cs & 0xFF])


def _wrap(reg: int, data: bytes) -> bytes:
    status = 0x00
    header = bytes([status, len(data)])
    cs = _checksum(header + data)
    return bytes([0xDD, reg, status, len(data)]) + data + cs + bytes([0x77])


def _basic_info_data(
    pack_mv: int = 5120, current_ma: int = 1240,
    soc: int = 83, cell_count: int = 4, temp_count: int = 1,
) -> bytes:
    data = struct.pack(
        '>HhHHHHHHH',
        pack_mv, current_ma,
        8300, 10000, 42, 0x0000, 0x0000, 0x0000, 0x0000,
    )
    data += bytes([0x20, soc, 0x03, cell_count, temp_count])
    for _ in range(temp_count):
        data += struct.pack('>H', 2981)  # 25.0°C
    return data


def test_make_read_request_basic_info():
    req = make_read_request(REG_BASIC)
    assert req == bytes([0xDD, 0xA5, 0x03, 0x00, 0xFF, 0xFD, 0x77])


def test_make_read_request_cells():
    req = make_read_request(REG_CELLS)
    assert req[0] == 0xDD
    assert req[2] == 0x04
    assert req[-1] == 0x77


def test_parse_basic_info():
    frame = _wrap(REG_BASIC, _basic_info_data())
    result = parse_response(frame)
    assert isinstance(result, BasicInfo)
    assert result.pack_voltage == pytest.approx(51.2, abs=0.01)
    assert result.current == pytest.approx(12.4, abs=0.01)
    assert result.soc == 83
    assert result.charge_fet is True
    assert result.discharge_fet is True
    assert len(result.temps) == 1
    assert result.temps[0] == pytest.approx(25.0, abs=0.1)


def test_parse_cell_voltages():
    voltages_mv = [3210, 3200, 3215, 3090]
    data = b"".join(struct.pack(">H", v) for v in voltages_mv)
    frame = _wrap(REG_CELLS, data)
    result = parse_response(frame)
    assert isinstance(result, CellVoltages)
    assert result.voltages[3] == pytest.approx(3.090, abs=0.001)
    assert result.delta == pytest.approx(0.125, abs=0.001)


def test_bad_checksum_raises():
    frame = bytearray(_wrap(REG_BASIC, _basic_info_data()))
    frame[-3] ^= 0xFF  # corrupt checksum
    with pytest.raises(ParseError):
        parse_response(bytes(frame))


def test_bad_start_byte_raises():
    frame = bytearray(_wrap(REG_BASIC, _basic_info_data()))
    frame[0] = 0xAA
    with pytest.raises(ParseError):
        parse_response(bytes(frame))
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/protocol/test_parser.py -v
```
Expected: ImportError.

- [ ] **Step 3: Write `bms_monitor/protocol/parser.py`**

```python
from __future__ import annotations
import struct
from bms_monitor.protocol.frames import BasicInfo, CellVoltages, BMSInfo, ProtectionFlags


class ParseError(Exception):
    pass


def _checksum(payload: bytes) -> bytes:
    cs = (~sum(payload) + 1) & 0xFFFF
    return bytes([cs >> 8, cs & 0xFF])


def make_read_request(register: int) -> bytes:
    payload = bytes([register, 0x00])
    cs = _checksum(payload)
    return bytes([0xDD, 0xA5, register, 0x00]) + cs + bytes([0x77])


def parse_response(data: bytes) -> BasicInfo | CellVoltages | BMSInfo:
    if len(data) < 7:
        raise ParseError("frame too short")
    if data[0] != 0xDD:
        raise ParseError(f"bad start byte: {data[0]:#x}")
    if data[-1] != 0x77:
        raise ParseError(f"bad end byte: {data[-1]:#x}")

    reg = data[1]
    status = data[2]
    length = data[3]
    payload = data[4: 4 + length]
    cs_received = data[4 + length: 4 + length + 2]
    cs_expected = _checksum(bytes([status, length]) + payload)

    if cs_received != cs_expected:
        raise ParseError(
            f"checksum mismatch: got {cs_received.hex()}, expected {cs_expected.hex()}"
        )
    if status != 0x00:
        raise ParseError(f"BMS reported error status: {status:#x}")

    if reg == 0x03:
        return _parse_basic_info(payload)
    if reg == 0x04:
        return _parse_cell_voltages(payload)
    if reg == 0x05:
        return _parse_bms_info(payload)
    raise ParseError(f"unknown register: {reg:#x}")


def _parse_basic_info(data: bytes) -> BasicInfo:
    if len(data) < 23:
        raise ParseError("BasicInfo payload too short")
    (
        pack_mv, current_ma, remaining, nominal,
        cycles, _prod_date, _bal_low, _bal_high, prot_mask,
    ) = struct.unpack_from(">HhHHHHHHH", data, 0)

    sw_ver, soc, fet, cell_count, temp_count = struct.unpack_from(">BBBBB", data, 18)
    temps = []
    for i in range(temp_count):
        raw, = struct.unpack_from(">H", data, 23 + i * 2)
        temps.append((raw - 2731) / 10.0)

    return BasicInfo(
        pack_voltage=pack_mv / 100.0,
        current=current_ma / 100.0,
        remaining_ah=remaining / 100.0,
        nominal_ah=nominal / 100.0,
        cycles=cycles,
        soc=soc,
        charge_fet=bool(fet & 0x01),
        discharge_fet=bool(fet & 0x02),
        cell_count=cell_count,
        temp_count=temp_count,
        temps=temps,
        protection=ProtectionFlags.from_bitmask(prot_mask),
        balance_bitmask=0,
    )


def _parse_cell_voltages(data: bytes) -> CellVoltages:
    count = len(data) // 2
    voltages = [
        struct.unpack_from(">H", data, i * 2)[0] / 1000.0
        for i in range(count)
    ]
    return CellVoltages(voltages=voltages)


def _parse_bms_info(data: bytes) -> BMSInfo:
    return BMSInfo(name=data.decode("ascii", errors="replace").strip())
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/protocol/ -v
```
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add bms_monitor/protocol/parser.py tests/protocol/test_parser.py
git commit -m "feat: JBD protocol parser with checksum validation"
```

---

## Task 4: Config

**Files:**
- Create: `bms_monitor/config.py`

- [ ] **Step 1: Write `bms_monitor/config.py`**

No failing test needed — pure I/O wrapper with a known default dict.

```python
from __future__ import annotations
import json
import os
from pathlib import Path

DEFAULT_SETTINGS: dict = {
    "cell_undervolt": 3.0,
    "cell_overvolt": 3.65,
    "pack_undervolt": 44.8,
    "temp_max": 45.0,
    "current_max": 100.0,
    "poll_interval": 1.0,
    "log_enabled": True,
    "log_dir": str(Path.home() / ".jbd-bms"),
}

_CONFIG_PATH = Path.home() / ".jbd-bms" / "settings.json"


def load_settings() -> dict:
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH) as f:
            saved = json.load(f)
        return {**DEFAULT_SETTINGS, **saved}
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_PATH, "w") as f:
        json.dump(settings, f, indent=2)
```

- [ ] **Step 2: Commit**

```bash
git add bms_monitor/config.py
git commit -m "feat: settings load/save"
```

---

## Task 5: Storage

**Files:**
- Create: `bms_monitor/storage/db.py`
- Create: `tests/storage/test_db.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/storage/test_db.py
import time, csv, io, pytest
from bms_monitor.storage.db import open_db, write_snapshot, query_snapshots, export_csv
from bms_monitor.protocol.frames import BasicInfo, CellVoltages, ProtectionFlags


def _make_info(soc=83, pack_voltage=51.2):
    return BasicInfo(
        pack_voltage=pack_voltage, current=12.4,
        remaining_ah=83.0, nominal_ah=100.0, cycles=42,
        soc=soc, charge_fet=True, discharge_fet=True,
        cell_count=4, temp_count=1, temps=[25.0],
        protection=ProtectionFlags.from_bitmask(0),
        balance_bitmask=0,
    )

def _make_cells():
    return CellVoltages(voltages=[3.21, 3.20, 3.21, 3.09])


def test_write_and_query(tmp_path):
    conn = open_db(str(tmp_path / "test.db"))
    t = time.time()
    write_snapshot(conn, _make_info(), _make_cells())
    rows = query_snapshots(conn, t - 1, t + 10)
    assert len(rows) == 1
    assert rows[0]["soc"] == 83
    assert rows[0]["pack_voltage"] == pytest.approx(51.2)
    conn.close()


def test_multiple_snapshots(tmp_path):
    conn = open_db(str(tmp_path / "test.db"))
    t = time.time()
    for soc in [80, 81, 82]:
        write_snapshot(conn, _make_info(soc=soc), _make_cells())
    rows = query_snapshots(conn, t - 1, t + 10)
    assert len(rows) == 3
    assert [r["soc"] for r in rows] == [80, 81, 82]
    conn.close()


def test_export_csv(tmp_path):
    conn = open_db(str(tmp_path / "test.db"))
    write_snapshot(conn, _make_info(), _make_cells())
    out = str(tmp_path / "export.csv")
    export_csv(conn, out)
    with open(out) as f:
        reader = list(csv.DictReader(f))
    assert len(reader) == 1
    assert float(reader[0]["pack_voltage"]) == pytest.approx(51.2)
    conn.close()
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/storage/ -v
```
Expected: ImportError.

- [ ] **Step 3: Write `bms_monitor/storage/db.py`**

```python
from __future__ import annotations
import csv
import json
import sqlite3
import time
from bms_monitor.protocol.frames import BasicInfo, CellVoltages

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    pack_voltage REAL,
    current REAL,
    soc INTEGER,
    remaining_ah REAL,
    temp1 REAL,
    temp2 REAL,
    cycles INTEGER,
    cell_voltages TEXT,
    charge_fet INTEGER,
    discharge_fet INTEGER,
    protection_flags TEXT
);
CREATE INDEX IF NOT EXISTS idx_ts ON snapshots(ts);
"""


def open_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def write_snapshot(conn: sqlite3.Connection, info: BasicInfo, cells: CellVoltages) -> None:
    conn.execute(
        """INSERT INTO snapshots
           (ts, pack_voltage, current, soc, remaining_ah,
            temp1, temp2, cycles, cell_voltages, charge_fet, discharge_fet, protection_flags)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            time.time(),
            info.pack_voltage, info.current, info.soc, info.remaining_ah,
            info.temps[0] if len(info.temps) > 0 else None,
            info.temps[1] if len(info.temps) > 1 else None,
            info.cycles,
            json.dumps(cells.voltages),
            int(info.charge_fet), int(info.discharge_fet),
            json.dumps({
                "cell_overvolt": info.protection.cell_overvolt,
                "cell_undervolt": info.protection.cell_undervolt,
                "short_circuit": info.protection.short_circuit,
            }),
        ),
    )
    conn.commit()


def query_snapshots(conn: sqlite3.Connection, start: float, end: float) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM snapshots WHERE ts >= ? AND ts <= ? ORDER BY ts",
        (start, end),
    ).fetchall()
    return [dict(r) for r in rows]


def export_csv(conn: sqlite3.Connection, path: str) -> None:
    rows = conn.execute("SELECT * FROM snapshots ORDER BY ts").fetchall()
    if not rows:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows([dict(r) for r in rows])
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/storage/ -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add bms_monitor/storage/db.py tests/storage/test_db.py
git commit -m "feat: SQLite storage with CSV export"
```

---

## Task 6: Alert checker

**Files:**
- Create: `bms_monitor/alerts/checker.py`
- Create: `tests/alerts/test_checker.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/alerts/test_checker.py
import time, pytest
from unittest.mock import MagicMock
from bms_monitor.alerts.checker import AlertChecker
from bms_monitor.protocol.frames import BasicInfo, CellVoltages, ProtectionFlags
from bms_monitor.config import DEFAULT_SETTINGS


def _info(pack_voltage=51.2, current=12.4, temps=None):
    return BasicInfo(
        pack_voltage=pack_voltage, current=current,
        remaining_ah=83.0, nominal_ah=100.0, cycles=42,
        soc=83, charge_fet=True, discharge_fet=True,
        cell_count=4, temp_count=1,
        temps=temps or [25.0],
        protection=ProtectionFlags.from_bitmask(0),
        balance_bitmask=0,
    )

def _cells(voltages=None):
    return CellVoltages(voltages=voltages or [3.21, 3.20, 3.21, 3.20])


def test_no_alert_when_normal(qapp):
    checker = AlertChecker(DEFAULT_SETTINGS)
    handler = MagicMock()
    checker.alert_triggered.connect(handler)
    checker.check(_info(), _cells())
    handler.assert_not_called()


def test_cell_undervolt_fires(qapp):
    checker = AlertChecker(DEFAULT_SETTINGS)  # cell_undervolt threshold = 3.0
    handler = MagicMock()
    checker.alert_triggered.connect(handler)
    checker.check(_info(), _cells(voltages=[3.21, 2.95, 3.21, 3.20]))
    handler.assert_called_once()
    title, msg = handler.call_args[0]
    assert "undervolt" in title.lower() or "undervolt" in msg.lower()


def test_overtemp_fires(qapp):
    checker = AlertChecker(DEFAULT_SETTINGS)  # temp_max = 45.0
    handler = MagicMock()
    checker.alert_triggered.connect(handler)
    checker.check(_info(temps=[50.0]), _cells())
    handler.assert_called_once()


def test_rate_limit(qapp):
    checker = AlertChecker(DEFAULT_SETTINGS)
    handler = MagicMock()
    checker.alert_triggered.connect(handler)
    cells = _cells(voltages=[3.21, 2.95, 3.21, 3.20])
    checker.check(_info(), cells)
    checker.check(_info(), cells)  # second check within 60s — should not re-fire
    assert handler.call_count == 1
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/alerts/ -v
```
Expected: ImportError.

- [ ] **Step 3: Write `bms_monitor/alerts/checker.py`**

```python
from __future__ import annotations
import time
from PyQt6.QtCore import QObject, pyqtSignal
from bms_monitor.protocol.frames import BasicInfo, CellVoltages

RATE_LIMIT_SECONDS = 60.0


class AlertChecker(QObject):
    alert_triggered = pyqtSignal(str, str)  # (title, message)

    def __init__(self, thresholds: dict, parent=None):
        super().__init__(parent)
        self._thresholds = thresholds
        self._last_fired: dict[str, float] = {}

    def check(self, info: BasicInfo, cells: CellVoltages) -> None:
        t = self._thresholds
        self._maybe_fire(
            "cell_undervolt",
            any(v < t["cell_undervolt"] for v in cells.voltages),
            "Cell Undervoltage",
            f"Cell voltage {min(cells.voltages):.3f}V below {t['cell_undervolt']}V",
        )
        self._maybe_fire(
            "cell_overvolt",
            any(v > t["cell_overvolt"] for v in cells.voltages),
            "Cell Overvoltage",
            f"Cell voltage {max(cells.voltages):.3f}V above {t['cell_overvolt']}V",
        )
        self._maybe_fire(
            "pack_undervolt",
            info.pack_voltage < t["pack_undervolt"],
            "Pack Undervoltage",
            f"Pack voltage {info.pack_voltage:.1f}V below {t['pack_undervolt']}V",
        )
        self._maybe_fire(
            "overtemp",
            any(temp > t["temp_max"] for temp in info.temps),
            "Overtemperature",
            f"Temperature {max(info.temps):.1f}°C above {t['temp_max']}°C",
        )
        self._maybe_fire(
            "overcurrent",
            abs(info.current) > t["current_max"],
            "Overcurrent",
            f"Current {info.current:.1f}A exceeds {t['current_max']}A",
        )
        if info.protection.any_fault:
            self._maybe_fire(
                "protection",
                True,
                "BMS Protection Triggered",
                "BMS has activated a protection flag — check connection.",
            )

    def _maybe_fire(self, key: str, condition: bool, title: str, msg: str) -> None:
        if not condition:
            return
        now = time.monotonic()
        if now - self._last_fired.get(key, 0) >= RATE_LIMIT_SECONDS:
            self._last_fired[key] = now
            self.alert_triggered.emit(title, msg)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/alerts/ -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add bms_monitor/alerts/checker.py tests/alerts/test_checker.py
git commit -m "feat: alert checker with rate limiting"
```

---

## Task 7: Serial transport

**Files:**
- Create: `bms_monitor/transport/base.py`
- Create: `bms_monitor/transport/serial.py`

- [ ] **Step 1: Write `bms_monitor/transport/base.py`**

```python
from PyQt6.QtCore import QObject, pyqtSignal


class Transport(QObject):
    frame_received = pyqtSignal(bytes)
    connection_changed = pyqtSignal(bool)   # True=connected
    error_occurred = pyqtSignal(str)

    def connect_device(self, target: str) -> None:
        raise NotImplementedError

    def disconnect_device(self) -> None:
        raise NotImplementedError

    def send_frame(self, data: bytes) -> None:
        raise NotImplementedError
```

- [ ] **Step 2: Write `bms_monitor/transport/serial.py`**

```python
from __future__ import annotations
import serial
from PyQt6.QtCore import QThread, pyqtSignal
from bms_monitor.transport.base import Transport

START_BYTE = 0xDD
END_BYTE = 0x77
MAX_FRAME = 256


class _ReaderThread(QThread):
    raw_frame = pyqtSignal(bytes)
    error = pyqtSignal(str)

    def __init__(self, port: serial.Serial):
        super().__init__()
        self._port = port
        self._running = True

    def run(self):
        buf = bytearray()
        while self._running:
            try:
                byte = self._port.read(1)
                if not byte:
                    continue
                b = byte[0]
                if b == START_BYTE and not buf:
                    buf.append(b)
                elif buf:
                    buf.append(b)
                    if b == END_BYTE and len(buf) >= 7:
                        self.raw_frame.emit(bytes(buf))
                        buf.clear()
                    elif len(buf) > MAX_FRAME:
                        buf.clear()
            except serial.SerialException as e:
                self.error.emit(str(e))
                break

    def stop(self):
        self._running = False


class SerialTransport(Transport):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._port: serial.Serial | None = None
        self._reader: _ReaderThread | None = None

    def connect_device(self, target: str) -> None:
        self._port = serial.Serial(target, baudrate=9600, timeout=1.0)
        self._reader = _ReaderThread(self._port)
        self._reader.raw_frame.connect(self.frame_received)
        self._reader.error.connect(self.error_occurred)
        self._reader.start()
        self.connection_changed.emit(True)

    def disconnect_device(self) -> None:
        if self._reader:
            self._reader.stop()
            self._reader.wait(2000)
        if self._port and self._port.is_open:
            self._port.close()
        self.connection_changed.emit(False)

    def send_frame(self, data: bytes) -> None:
        if self._port and self._port.is_open:
            self._port.write(data)
```

- [ ] **Step 3: Smoke test — verify import and instantiation**

```bash
python -c "from bms_monitor.transport.serial import SerialTransport; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add bms_monitor/transport/base.py bms_monitor/transport/serial.py
git commit -m "feat: serial transport with QThread frame reader"
```

---

## Task 8: BLE transport

**Files:**
- Create: `bms_monitor/transport/ble.py`

- [ ] **Step 1: Write `bms_monitor/transport/ble.py`**

```python
from __future__ import annotations
import asyncio
import threading
from bleak import BleakClient, BleakScanner
from PyQt6.QtCore import QObject
from bms_monitor.transport.base import Transport

BLE_SERVICE_UUID  = "0000ff00-0000-1000-8000-00805f9b34fb"
BLE_TX_CHAR_UUID  = "0000ff01-0000-1000-8000-00805f9b34fb"  # notify (BMS → app)
BLE_RX_CHAR_UUID  = "0000ff02-0000-1000-8000-00805f9b34fb"  # write  (app → BMS)


class BLETransport(Transport):
    """Runs bleak in a dedicated asyncio thread. Delivers frames via Qt signal."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._client: BleakClient | None = None
        self._buf = bytearray()

    # ------------------------------------------------------------------ public
    def connect_device(self, target: str) -> None:
        """target = BLE device address or name substring for scan."""
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop, args=(target,), daemon=True
        )
        self._thread.start()

    def disconnect_device(self) -> None:
        if self._loop and self._client:
            asyncio.run_coroutine_threadsafe(self._client.disconnect(), self._loop)

    def send_frame(self, data: bytes) -> None:
        if self._loop and self._client:
            asyncio.run_coroutine_threadsafe(
                self._client.write_gatt_char(BLE_RX_CHAR_UUID, data, response=False),
                self._loop,
            )

    # ----------------------------------------------------------------- private
    def _run_loop(self, target: str) -> None:
        self._loop.run_until_complete(self._connect_and_run(target))

    async def _connect_and_run(self, target: str) -> None:
        address = await self._resolve_address(target)
        if not address:
            self._emit_error(f"BLE device not found: {target!r}")
            return
        try:
            async with BleakClient(address) as client:
                self._client = client
                await client.start_notify(BLE_TX_CHAR_UUID, self._on_notify)
                self._emit_connected(True)
                # keep alive until disconnect
                while client.is_connected:
                    await asyncio.sleep(0.5)
        except Exception as e:
            self._emit_error(str(e))
        finally:
            self._emit_connected(False)

    async def _resolve_address(self, target: str) -> str | None:
        # If it looks like a MAC/UUID address, use directly
        if ":" in target or "-" in target:
            return target
        # Otherwise scan for a device whose name contains target
        devices = await BleakScanner.discover(timeout=5.0)
        for d in devices:
            if target.lower() in (d.name or "").lower():
                return d.address
        return None

    def _on_notify(self, _handle: int, data: bytearray) -> None:
        self._buf.extend(data)
        # extract complete frames
        while True:
            start = self._buf.find(0xDD)
            if start == -1:
                self._buf.clear()
                break
            if start > 0:
                del self._buf[:start]
            end = self._buf.find(0x77, 4)
            if end == -1:
                break
            frame = bytes(self._buf[: end + 1])
            del self._buf[: end + 1]
            self._emit_frame(frame)

    def _emit_frame(self, frame: bytes) -> None:
        self.frame_received.emit(frame)  # safe: Qt queues cross-thread signals

    def _emit_connected(self, state: bool) -> None:
        self.connection_changed.emit(state)

    def _emit_error(self, msg: str) -> None:
        self.error_occurred.emit(msg)
```

- [ ] **Step 2: Smoke test**

```bash
python -c "from bms_monitor.transport.ble import BLETransport; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add bms_monitor/transport/ble.py
git commit -m "feat: BLE transport via bleak asyncio thread"
```

---

## Task 9: Simulator

**Files:**
- Create: `bms_monitor/simulator/simulator.py`
- Create: `tests/simulator/test_simulator.py`

- [ ] **Step 1: Verify socat is available**

```bash
which socat || sudo apt install socat
```

- [ ] **Step 2: Write failing test**

```python
# tests/simulator/test_simulator.py
import time, subprocess, serial, pytest
from bms_monitor.simulator.simulator import BMSSimulator
from bms_monitor.protocol.parser import make_read_request, parse_response
from bms_monitor.protocol.frames import BasicInfo, CellVoltages


def test_simulator_responds_to_basic_info():
    sim = BMSSimulator(scenario="normal", cell_count=4)
    sim.start()
    time.sleep(0.5)  # let socat create ptys
    try:
        port = serial.Serial(sim.app_port, baudrate=9600, timeout=2.0)
        port.write(make_read_request(0x03))
        raw = port.read(256)
        port.close()
        assert len(raw) >= 7
        result = parse_response(raw[:raw.index(0x77) + 1])
        assert isinstance(result, BasicInfo)
        assert 40.0 < result.pack_voltage < 70.0
    finally:
        sim.stop()


def test_simulator_responds_to_cell_voltages():
    sim = BMSSimulator(scenario="normal", cell_count=4)
    sim.start()
    time.sleep(0.5)
    try:
        port = serial.Serial(sim.app_port, baudrate=9600, timeout=2.0)
        port.write(make_read_request(0x04))
        raw = port.read(256)
        port.close()
        result = parse_response(raw[:raw.index(0x77) + 1])
        assert isinstance(result, CellVoltages)
        assert len(result.voltages) == 4
    finally:
        sim.stop()
```

- [ ] **Step 3: Write `bms_monitor/simulator/simulator.py`**

```python
from __future__ import annotations
import math
import os
import random
import serial
import struct
import subprocess
import tempfile
import threading
import time
from bms_monitor.protocol.frames import BasicInfo, CellVoltages, ProtectionFlags

START = 0xDD
END   = 0x77
READ_CMD = 0xA5


def _checksum(payload: bytes) -> bytes:
    cs = (~sum(payload) + 1) & 0xFFFF
    return bytes([cs >> 8, cs & 0xFF])


def _make_response(reg: int, data: bytes) -> bytes:
    status = 0x00
    header = bytes([status, len(data)])
    cs = _checksum(header + data)
    return bytes([START, reg, status, len(data)]) + data + cs + bytes([END])


def _encode_basic_info(state: dict, cell_count: int) -> bytes:
    pack_mv = int(state["pack_voltage"] * 100)
    current_ma = int(state["current"] * 100)
    remaining = int(state["remaining_ah"] * 100)
    nominal = int(state["nominal_ah"] * 100)
    temp_raw = int(state["temp"] * 10 + 2731)
    data = struct.pack(
        ">HhHHHHHHH",
        pack_mv, current_ma, remaining, nominal,
        state["cycles"], 0x0000, 0x0000, 0x0000,
        state["protection_mask"],
    )
    data += bytes([0x20, state["soc"], 0x03, cell_count, 1])
    data += struct.pack(">H", temp_raw)
    return data


def _encode_cell_voltages(voltages: list[float]) -> bytes:
    return b"".join(struct.pack(">H", int(v * 1000)) for v in voltages)


class BMSSimulator:
    def __init__(self, scenario: str = "normal", cell_count: int = 16):
        self.scenario = scenario
        self.cell_count = cell_count
        self.app_port = "/tmp/bms-app"
        self.sim_port = "/tmp/bms-sim"
        self._socat: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._t0 = time.monotonic()
        self._state = self._initial_state()

    def _initial_state(self) -> dict:
        return {
            "pack_voltage": 51.2,
            "current": -5.0,     # discharging
            "remaining_ah": 83.0,
            "nominal_ah": 100.0,
            "soc": 83,
            "temp": 25.0,
            "cycles": 42,
            "protection_mask": 0x0000,
        }

    def _cell_voltages(self) -> list[float]:
        base = self._state["pack_voltage"] / self.cell_count
        voltages = []
        for i in range(self.cell_count):
            noise = random.gauss(0, 0.002)
            v = base + noise
            if self.scenario == "cell-drift" and i == 0:
                elapsed = time.monotonic() - self._t0
                v -= min(elapsed * 0.001, 0.15)  # drift up to 150mV
            voltages.append(round(v, 3))
        return voltages

    def _tick(self) -> None:
        elapsed = time.monotonic() - self._t0
        s = self._state
        s["temp"] = 25.0 + math.sin(elapsed / 60) * 2
        if self.scenario == "overtemp":
            s["temp"] = min(25.0 + elapsed * 0.5, 55.0)
        if self.scenario == "overvoltage" and elapsed > 5:
            s["protection_mask"] = 0x0001
        if self.scenario == "normal":
            s["pack_voltage"] = 51.2 - (elapsed / 3600) * 0.5
            s["soc"] = max(0, 83 - int(elapsed / 120))

    def start(self) -> None:
        for p in (self.app_port, self.sim_port):
            if os.path.exists(p):
                os.unlink(p)
        self._socat = subprocess.Popen(
            ["socat", "-d", "-d",
             f"pty,raw,echo=0,link={self.app_port}",
             f"pty,raw,echo=0,link={self.sim_port}"],
            stderr=subprocess.DEVNULL,
        )
        time.sleep(0.3)
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._socat:
            self._socat.terminate()

    def _serve(self) -> None:
        while self._running:
            try:
                port = serial.Serial(self.sim_port, baudrate=9600, timeout=0.5)
                break
            except serial.SerialException:
                time.sleep(0.1)

        buf = bytearray()
        while self._running:
            try:
                byte = port.read(1)
                if not byte:
                    continue
                buf.extend(byte)
                if len(buf) >= 7 and buf[-1] == END:
                    self._handle_request(port, bytes(buf))
                    buf.clear()
                    self._tick()
                elif len(buf) > 16:
                    buf.clear()
            except Exception:
                break

    def _handle_request(self, port: serial.Serial, req: bytes) -> None:
        if len(req) < 4 or req[0] != START or req[1] != READ_CMD:
            return
        reg = req[2]
        if self.scenario == "disconnect":
            return  # silence
        if reg == 0x03:
            data = _encode_basic_info(self._state, self.cell_count)
            port.write(_make_response(0x03, data))
        elif reg == 0x04:
            data = _encode_cell_voltages(self._cell_voltages())
            port.write(_make_response(0x04, data))
        elif reg == 0x05:
            port.write(_make_response(0x05, b"JBD-SP04S034"))
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/simulator/ -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add bms_monitor/simulator/simulator.py tests/simulator/test_simulator.py
git commit -m "feat: BMS simulator with socat virtual serial port"
```

---

## Task 10: UI — main window

**Files:**
- Create: `bms_monitor/ui/main_window.py`

- [ ] **Step 1: Write `bms_monitor/ui/main_window.py`**

```python
from __future__ import annotations
import time
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QStatusBar, QSystemTrayIcon, QMenu,
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QIcon
import serial.tools.list_ports

from bms_monitor.config import load_settings, save_settings
from bms_monitor.protocol.parser import make_read_request, parse_response, ParseError
from bms_monitor.protocol.frames import BasicInfo, CellVoltages
from bms_monitor.transport.serial import SerialTransport
from bms_monitor.transport.ble import BLETransport
from bms_monitor.storage.db import open_db, write_snapshot
from bms_monitor.alerts.checker import AlertChecker
from bms_monitor.ui.widgets.stats_row import StatsRow
from bms_monitor.ui.widgets.cells_widget import CellsWidget
from bms_monitor.ui.widgets.live_chart import LiveChart
from bms_monitor.ui.widgets.settings_panel import SettingsPanel
from bms_monitor.ui.widgets.alerts_banner import AlertsBanner

import sqlite3, os
from datetime import datetime


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JBD BMS Monitor")
        self.setMinimumSize(900, 650)

        self._settings = load_settings()
        self._transport = None
        self._db: sqlite3.Connection | None = None
        self._last_basic: BasicInfo | None = None
        self._last_cells: CellVoltages | None = None
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll)
        self._checker = AlertChecker(self._settings)
        self._checker.alert_triggered.connect(self._on_alert)

        self._build_ui()
        self._build_tray()

    # ---------------------------------------------------------------- UI build
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(6)
        root.setContentsMargins(8, 8, 8, 8)

        root.addLayout(self._build_toolbar())

        self._alerts_banner = AlertsBanner()
        root.addWidget(self._alerts_banner)

        self._stats_row = StatsRow()
        root.addWidget(self._stats_row)

        middle = QHBoxLayout()
        self._cells_widget = CellsWidget()
        middle.addWidget(self._cells_widget, stretch=3)

        self._settings_panel = SettingsPanel(self._settings, self)
        self._settings_panel.setVisible(False)
        self._settings_panel.settings_saved.connect(self._on_settings_saved)

        from bms_monitor.ui.widgets.fets_flags import FetsFlagsWidget
        self._fets_flags = FetsFlagsWidget()
        middle.addWidget(self._fets_flags, stretch=1)
        root.addLayout(middle)

        self._live_chart = LiveChart()
        root.addWidget(self._live_chart)

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Disconnected")

    def _build_toolbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()

        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(160)
        self._refresh_ports()
        bar.addWidget(QLabel("Port:"))
        bar.addWidget(self._port_combo)

        self._ble_btn = QPushButton("BLE Scan…")
        self._ble_btn.clicked.connect(self._ble_scan)
        bar.addWidget(self._ble_btn)

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.clicked.connect(self._toggle_connect)
        bar.addWidget(self._connect_btn)

        bar.addStretch()

        self._poll_combo = QComboBox()
        for label, secs in [("0.5s", 0.5), ("1s", 1.0), ("2s", 2.0), ("5s", 5.0)]:
            self._poll_combo.addItem(label, secs)
        self._poll_combo.setCurrentIndex(1)
        bar.addWidget(QLabel("Poll:"))
        bar.addWidget(self._poll_combo)

        settings_btn = QPushButton("⚙ Settings")
        settings_btn.clicked.connect(self._toggle_settings)
        bar.addWidget(settings_btn)

        return bar

    def _build_tray(self) -> None:
        self._tray = QSystemTrayIcon(self)
        self._tray.setToolTip("JBD BMS Monitor")
        menu = QMenu()
        menu.addAction("Show").triggered.connect(self.show)
        menu.addAction("Quit").triggered.connect(self.close)
        self._tray.setContextMenu(menu)
        self._tray.show()

    # ----------------------------------------------------------- connection
    def _refresh_ports(self) -> None:
        self._port_combo.clear()
        for p in serial.tools.list_ports.comports():
            self._port_combo.addItem(p.device)
        self._port_combo.addItem("BLE (use scan)")

    def _toggle_connect(self) -> None:
        if self._transport is None:
            self._do_connect()
        else:
            self._do_disconnect()

    def _do_connect(self) -> None:
        target = self._port_combo.currentText()
        if target.startswith("BLE"):
            self._transport = BLETransport(self)
        else:
            self._transport = SerialTransport(self)

        self._transport.frame_received.connect(self._on_frame)
        self._transport.connection_changed.connect(self._on_connection_changed)
        self._transport.error_occurred.connect(self._on_error)
        self._transport.connect_device(target)

        if self._settings.get("log_enabled"):
            log_dir = os.path.expanduser(self._settings.get("log_dir", "~/.jbd-bms"))
            os.makedirs(log_dir, exist_ok=True)
            db_path = os.path.join(log_dir, f"bms_{datetime.now():%Y-%m-%d}.db")
            self._db = open_db(db_path)
            self._status_bar.showMessage(f"Logging to {db_path}")

        interval_ms = int(self._poll_combo.currentData() * 1000)
        self._poll_timer.start(interval_ms)
        self._connect_btn.setText("Disconnect")

    def _do_disconnect(self) -> None:
        self._poll_timer.stop()
        if self._transport:
            self._transport.disconnect_device()
            self._transport = None
        if self._db:
            self._db.close()
            self._db = None
        self._connect_btn.setText("Connect")

    def _ble_scan(self) -> None:
        from bms_monitor.ui.widgets.ble_scan_dialog import BLEScanDialog
        dlg = BLEScanDialog(self)
        if dlg.exec():
            address = dlg.selected_address()
            self._port_combo.addItem(address)
            self._port_combo.setCurrentText(address)

    # ----------------------------------------------------------- data
    def _poll(self) -> None:
        if self._transport:
            self._transport.send_frame(make_read_request(0x03))
            self._transport.send_frame(make_read_request(0x04))

    def _on_frame(self, raw: bytes) -> None:
        try:
            result = parse_response(raw)
        except ParseError:
            return

        if isinstance(result, BasicInfo):
            self._last_basic = result
            self._stats_row.update(result)
            self._fets_flags.update(result)
            self._live_chart.push_basic(result)
            if self._last_cells:
                self._checker.check(result, self._last_cells)
                if self._db:
                    write_snapshot(self._db, result, self._last_cells)

        elif isinstance(result, CellVoltages):
            self._last_cells = result
            self._cells_widget.update(result)

    def _on_connection_changed(self, connected: bool) -> None:
        if connected:
            self._status_bar.showMessage("Connected")
        else:
            self._do_disconnect()
            self._status_bar.showMessage("Disconnected")

    def _on_error(self, msg: str) -> None:
        self._status_bar.showMessage(f"Error: {msg}")

    def _on_alert(self, title: str, msg: str) -> None:
        self._alerts_banner.show_alert(title, msg)
        self._tray.showMessage(title, msg, QSystemTrayIcon.MessageIcon.Warning, 5000)

    def _toggle_settings(self) -> None:
        self._settings_panel.setVisible(not self._settings_panel.isVisible())
        if self._settings_panel.isVisible():
            self._settings_panel.show()

    def _on_settings_saved(self, new_settings: dict) -> None:
        self._settings = new_settings
        save_settings(new_settings)
        self._checker = AlertChecker(new_settings)
        self._checker.alert_triggered.connect(self._on_alert)
```

- [ ] **Step 2: Commit (stubs — widgets written in next tasks)**

```bash
git add bms_monitor/ui/main_window.py
git commit -m "feat: main window layout and signal wiring (widget stubs pending)"
```

---

## Task 11: UI widgets

**Files:**
- Create: `bms_monitor/ui/widgets/stats_row.py`
- Create: `bms_monitor/ui/widgets/cells_widget.py`
- Create: `bms_monitor/ui/widgets/live_chart.py`
- Create: `bms_monitor/ui/widgets/fets_flags.py`
- Create: `bms_monitor/ui/widgets/alerts_banner.py`
- Create: `bms_monitor/ui/widgets/history_widget.py`
- Create: `bms_monitor/ui/widgets/settings_panel.py`
- Create: `bms_monitor/ui/widgets/ble_scan_dialog.py`

- [ ] **Step 1: Write `bms_monitor/ui/widgets/stats_row.py`**

```python
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout, QFrame
from PyQt6.QtCore import Qt
from bms_monitor.protocol.frames import BasicInfo


class _Tile(QFrame):
    def __init__(self, label: str):
        super().__init__()
        self.setFrameShape(QFrame.Shape.Box)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        self._label = QLabel(label)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("color: #888; font-size: 10px;")
        self._value = QLabel("--")
        self._value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self._label)
        layout.addWidget(self._value)

    def set_value(self, text: str, color: str = "#4ecdc4") -> None:
        self._value.setText(text)
        self._value.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color};")


class StatsRow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)
        self._voltage = _Tile("PACK VOLTAGE")
        self._current = _Tile("CURRENT")
        self._soc     = _Tile("SOC")
        self._remain  = _Tile("REMAINING")
        self._temp    = _Tile("TEMP 1")
        self._cycles  = _Tile("CYCLES")
        for tile in (self._voltage, self._current, self._soc,
                     self._remain, self._temp, self._cycles):
            layout.addWidget(tile)

    def update(self, info: BasicInfo) -> None:
        self._voltage.set_value(f"{info.pack_voltage:.1f}V")
        color = "#f5a623" if info.current >= 0 else "#4ecdc4"
        self._current.set_value(f"{info.current:+.1f}A", color)
        self._soc.set_value(f"{info.soc}%", "#45b7d1")
        self._remain.set_value(f"{info.remaining_ah:.1f}Ah", "#96ceb4")
        temp = info.temps[0] if info.temps else 0
        t_color = "#e94560" if temp > 40 else "#ffeaa7"
        self._temp.set_value(f"{temp:.1f}°C", t_color)
        self._cycles.set_value(str(info.cycles), "#a29bfe")
```

- [ ] **Step 2: Write `bms_monitor/ui/widgets/cells_widget.py`**

```python
from PyQt6.QtWidgets import QWidget, QGridLayout, QLabel, QProgressBar, QVBoxLayout
from PyQt6.QtCore import Qt
from bms_monitor.protocol.frames import CellVoltages


class CellsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._layout = QGridLayout(self)
        self._layout.setSpacing(4)
        self._bars: list[tuple[QProgressBar, QLabel]] = []

    def update(self, cells: CellVoltages) -> None:
        count = len(cells.voltages)
        # rebuild bars if cell count changed
        if len(self._bars) != count:
            for i in reversed(range(self._layout.count())):
                self._layout.itemAt(i).widget().deleteLater()
            self._bars = []
            cols = 8
            for i in range(count):
                bar = QProgressBar()
                bar.setOrientation(Qt.Orientation.Vertical)
                bar.setRange(2800, 3700)  # mV
                bar.setTextVisible(False)
                bar.setFixedWidth(28)
                lbl = QLabel("--")
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet("font-size: 9px;")
                col = i % cols
                row_bar = (i // cols) * 2
                self._layout.addWidget(bar, row_bar, col)
                self._layout.addWidget(lbl, row_bar + 1, col)
                self._bars.append((bar, lbl))

        min_v = cells.min_voltage
        for i, (bar, lbl) in enumerate(self._bars):
            v = cells.voltages[i]
            bar.setValue(int(v * 1000))
            lbl.setText(f"{v:.3f}")
            is_low = (cells.delta > 0.020 and abs(v - min_v) < 0.001)
            color = "#e94560" if is_low else "#4ecdc4"
            bar.setStyleSheet(f"QProgressBar::chunk {{ background: {color}; }}")
            lbl.setStyleSheet(f"font-size: 9px; color: {color};")

        # show delta in tooltip
        self.setToolTip(f"Δ max: {cells.delta * 1000:.0f} mV")
```

- [ ] **Step 3: Write `bms_monitor/ui/widgets/live_chart.py`**

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
import pyqtgraph as pg
from bms_monitor.protocol.frames import BasicInfo
from collections import deque
import time

HISTORY = 300  # samples


class LiveChart(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._plot = pg.PlotWidget(background="#16213e")
        self._plot.showGrid(x=True, y=True, alpha=0.2)
        self._plot.setLabel("left", "Voltage (V)")
        self._plot.setLabel("bottom", "Time (s)")

        self._v_curve = self._plot.plot(pen=pg.mkPen("#4ecdc4", width=2), name="Voltage")
        self._i_curve = self._plot.plot(pen=pg.mkPen("#f5a623", width=2), name="Current")

        layout.addWidget(self._plot)

        self._times: deque[float] = deque(maxlen=HISTORY)
        self._voltages: deque[float] = deque(maxlen=HISTORY)
        self._currents: deque[float] = deque(maxlen=HISTORY)
        self._t0 = time.monotonic()

    def push_basic(self, info: BasicInfo) -> None:
        t = time.monotonic() - self._t0
        self._times.append(t)
        self._voltages.append(info.pack_voltage)
        self._currents.append(info.current)
        ts = list(self._times)
        self._v_curve.setData(ts, list(self._voltages))
        self._i_curve.setData(ts, list(self._currents))
```

- [ ] **Step 4: Write `bms_monitor/ui/widgets/fets_flags.py`**

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt
from bms_monitor.protocol.frames import BasicInfo


class FetsFlagsWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel("FET STATUS"))
        self._charge_lbl = QLabel("Charge: --")
        self._discharge_lbl = QLabel("Discharge: --")
        layout.addWidget(self._charge_lbl)
        layout.addWidget(self._discharge_lbl)

        layout.addSpacing(8)
        layout.addWidget(QLabel("PROTECTION FLAGS"))

        self._flag_labels: dict[str, QLabel] = {}
        for name in ["cell_overvolt", "cell_undervolt", "pack_overvolt",
                     "pack_undervolt", "charge_overcurrent",
                     "discharge_overcurrent", "short_circuit", "ic_error"]:
            lbl = QLabel(f"  {name.replace('_', ' ')}")
            lbl.setStyleSheet("color: #555; font-size: 10px;")
            layout.addWidget(lbl)
            self._flag_labels[name] = lbl
        layout.addStretch()

    def update(self, info: BasicInfo) -> None:
        c = "#4ecdc4" if info.charge_fet else "#e94560"
        d = "#4ecdc4" if info.discharge_fet else "#e94560"
        self._charge_lbl.setStyleSheet(f"color: {c};")
        self._charge_lbl.setText(f"Charge: {'ON' if info.charge_fet else 'OFF'}")
        self._discharge_lbl.setStyleSheet(f"color: {d};")
        self._discharge_lbl.setText(f"Discharge: {'ON' if info.discharge_fet else 'OFF'}")

        p = info.protection
        flag_map = {
            "cell_overvolt": p.cell_overvolt,
            "cell_undervolt": p.cell_undervolt,
            "pack_overvolt": p.pack_overvolt,
            "pack_undervolt": p.pack_undervolt,
            "charge_overcurrent": p.charge_overcurrent,
            "discharge_overcurrent": p.discharge_overcurrent,
            "short_circuit": p.short_circuit,
            "ic_error": p.ic_error,
        }
        for name, active in flag_map.items():
            color = "#e94560" if active else "#555"
            prefix = "▶" if active else "  "
            self._flag_labels[name].setStyleSheet(f"color: {color}; font-size: 10px;")
            self._flag_labels[name].setText(f"{prefix} {name.replace('_', ' ')}")
```

- [ ] **Step 5: Write `bms_monitor/ui/widgets/alerts_banner.py`**

```python
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import QTimer


class AlertsBanner(QWidget):
    def __init__(self):
        super().__init__()
        self.setVisible(False)
        self.setStyleSheet("background: #e94560; border-radius: 4px;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        self._label = QLabel()
        self._label.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(self._label)
        layout.addStretch()
        dismiss = QPushButton("✕")
        dismiss.setFlat(True)
        dismiss.setStyleSheet("color: white;")
        dismiss.clicked.connect(self.setVisible(False))
        layout.addWidget(dismiss)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(lambda: self.setVisible(False))

    def show_alert(self, title: str, msg: str) -> None:
        self._label.setText(f"⚠ {title}: {msg}")
        self.setVisible(True)
        self._timer.start(10_000)  # auto-dismiss after 10s
```

- [ ] **Step 6: Write `bms_monitor/ui/widgets/settings_panel.py`**

```python
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QDoubleSpinBox, QCheckBox,
    QLineEdit, QPushButton, QDialogButtonBox,
)
from PyQt6.QtCore import pyqtSignal


class SettingsPanel(QDialog):
    settings_saved = pyqtSignal(dict)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self._settings = dict(settings)
        form = QFormLayout(self)

        self._cell_uv = QDoubleSpinBox(); self._cell_uv.setRange(2.0, 3.5); self._cell_uv.setSingleStep(0.01)
        self._cell_ov = QDoubleSpinBox(); self._cell_ov.setRange(3.0, 4.5); self._cell_ov.setSingleStep(0.01)
        self._pack_uv = QDoubleSpinBox(); self._pack_uv.setRange(10.0, 100.0); self._pack_uv.setSingleStep(0.1)
        self._temp_max = QDoubleSpinBox(); self._temp_max.setRange(20.0, 80.0)
        self._current_max = QDoubleSpinBox(); self._current_max.setRange(1.0, 500.0)
        self._log_enabled = QCheckBox()
        self._log_dir = QLineEdit()

        form.addRow("Cell undervolt (V):", self._cell_uv)
        form.addRow("Cell overvolt (V):", self._cell_ov)
        form.addRow("Pack undervolt (V):", self._pack_uv)
        form.addRow("Max temp (°C):", self._temp_max)
        form.addRow("Max current (A):", self._current_max)
        form.addRow("Enable logging:", self._log_enabled)
        form.addRow("Log directory:", self._log_dir)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        self._load()

    def _load(self) -> None:
        s = self._settings
        self._cell_uv.setValue(s.get("cell_undervolt", 3.0))
        self._cell_ov.setValue(s.get("cell_overvolt", 3.65))
        self._pack_uv.setValue(s.get("pack_undervolt", 44.8))
        self._temp_max.setValue(s.get("temp_max", 45.0))
        self._current_max.setValue(s.get("current_max", 100.0))
        self._log_enabled.setChecked(s.get("log_enabled", True))
        self._log_dir.setText(s.get("log_dir", "~/.jbd-bms"))

    def _save(self) -> None:
        self._settings.update({
            "cell_undervolt": self._cell_uv.value(),
            "cell_overvolt": self._cell_ov.value(),
            "pack_undervolt": self._pack_uv.value(),
            "temp_max": self._temp_max.value(),
            "current_max": self._current_max.value(),
            "log_enabled": self._log_enabled.isChecked(),
            "log_dir": self._log_dir.text(),
        })
        self.settings_saved.emit(self._settings)
        self.accept()
```

- [ ] **Step 7: Write `bms_monitor/ui/widgets/history_widget.py`**

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog
import pyqtgraph as pg
import sqlite3
import json
from bms_monitor.storage.db import query_snapshots, export_csv
import time


class HistoryWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self._btn_1h = QPushButton("Last 1h"); self._btn_1h.clicked.connect(lambda: self._load(3600))
        self._btn_6h = QPushButton("Last 6h"); self._btn_6h.clicked.connect(lambda: self._load(21600))
        self._btn_24h = QPushButton("Last 24h"); self._btn_24h.clicked.connect(lambda: self._load(86400))
        self._btn_export = QPushButton("Export CSV"); self._btn_export.clicked.connect(self._export)
        for btn in (self._btn_1h, self._btn_6h, self._btn_24h, self._btn_export):
            controls.addWidget(btn)
        controls.addStretch()
        layout.addLayout(controls)

        self._plot = pg.PlotWidget(background="#16213e")
        self._plot.showGrid(x=True, y=True, alpha=0.2)
        self._v_curve = self._plot.plot(pen=pg.mkPen("#4ecdc4", width=2), name="Voltage")
        self._soc_curve = self._plot.plot(pen=pg.mkPen("#45b7d1", width=1), name="SOC")
        layout.addWidget(self._plot)

        self._conn: sqlite3.Connection | None = None

    def set_db(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def _load(self, seconds: int) -> None:
        if not self._conn:
            return
        now = time.time()
        rows = query_snapshots(self._conn, now - seconds, now)
        if not rows:
            return
        ts = [r["ts"] - rows[0]["ts"] for r in rows]
        vs = [r["pack_voltage"] for r in rows]
        socs = [r["soc"] for r in rows]
        self._v_curve.setData(ts, vs)
        self._soc_curve.setData(ts, socs)

    def _export(self) -> None:
        if not self._conn:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV Files (*.csv)")
        if path:
            export_csv(self._conn, path)
```

- [ ] **Step 8: Write `bms_monitor/ui/widgets/ble_scan_dialog.py`**

```python
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QDialogButtonBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import asyncio
from bleak import BleakScanner


class _ScanThread(QThread):
    found = pyqtSignal(str, str)  # (name, address)
    done = pyqtSignal()

    def run(self):
        async def scan():
            devices = await BleakScanner.discover(timeout=5.0)
            for d in devices:
                self.found.emit(d.name or "Unknown", d.address)
        asyncio.run(scan())
        self.done.emit()


class BLEScanDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BLE Scan")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        self._status = QLabel("Scanning for 5 seconds…")
        layout.addWidget(self._status)
        self._list = QListWidget()
        layout.addWidget(self._list)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._thread = _ScanThread()
        self._thread.found.connect(self._add_device)
        self._thread.done.connect(lambda: self._status.setText("Scan complete."))
        self._thread.start()

    def _add_device(self, name: str, address: str) -> None:
        item = QListWidgetItem(f"{name}  [{address}]")
        item.setData(Qt.ItemDataRole.UserRole, address)
        self._list.addItem(item)

    def selected_address(self) -> str:
        item = self._list.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return ""
```

- [ ] **Step 9: Smoke test all widgets instantiate**

```bash
python -c "
import sys
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)
from bms_monitor.ui.widgets.stats_row import StatsRow
from bms_monitor.ui.widgets.cells_widget import CellsWidget
from bms_monitor.ui.widgets.live_chart import LiveChart
from bms_monitor.ui.widgets.fets_flags import FetsFlagsWidget
from bms_monitor.ui.widgets.alerts_banner import AlertsBanner
StatsRow(); CellsWidget(); LiveChart(); FetsFlagsWidget(); AlertsBanner()
print('All widgets OK')
"
```
Expected: `All widgets OK`

- [ ] **Step 10: Commit**

```bash
git add bms_monitor/ui/
git commit -m "feat: all UI widgets (stats, cells, chart, flags, alerts, settings, BLE scan)"
```

---

## Task 12: Entry points

**Files:**
- Create: `main.py`
- Create: `simulator_main.py`

- [ ] **Step 1: Write `main.py`**

```python
import sys
from PyQt6.QtWidgets import QApplication
from bms_monitor.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("JBD BMS Monitor")
    app.setStyle("Fusion")
    # Dark palette
    from PyQt6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#1a1a2e"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e2e2e2"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#16213e"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#0f3460"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#16213e"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e2e2e2"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#e94560"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write `simulator_main.py`**

```python
import argparse, time, signal, sys
from bms_monitor.simulator.simulator import BMSSimulator

SCENARIOS = ["normal", "cell-drift", "overvoltage", "overtemp", "disconnect"]


def main():
    parser = argparse.ArgumentParser(description="JBD BMS Simulator")
    parser.add_argument("--scenario", choices=SCENARIOS, default="normal")
    parser.add_argument("--cells", type=int, default=16, help="Number of cells (default: 16)")
    args = parser.parse_args()

    sim = BMSSimulator(scenario=args.scenario, cell_count=args.cells)
    sim.start()
    print(f"Simulator running — scenario: {args.scenario}, cells: {args.cells}")
    print(f"Connect the app to: {sim.app_port}")
    print("Press Ctrl+C to stop.")

    def _stop(sig, frame):
        print("\nStopping simulator…")
        sim.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _stop)
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify app launches**

```bash
# In terminal 1 — start simulator
python simulator_main.py --scenario normal --cells 4

# In terminal 2 — launch app (select /tmp/bms-app, click Connect)
python main.py
```

- [ ] **Step 4: Commit**

```bash
git add main.py simulator_main.py
git commit -m "feat: entry points for app and simulator"
```

---

## Task 13: README and packaging

**Files:**
- Create: `README.md`
- Finalize: `pyproject.toml`

- [ ] **Step 1: Write `README.md`**

```markdown
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
sudo apt install socat   # Debian/Ubuntu/Arch
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
```

- [ ] **Step 2: Run full test suite**

```bash
pytest tests/ -v
```
Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: README with install, usage, simulator, and hardware notes"
```

---

## Task 14: Create GitHub repo and push

- [ ] **Step 1: Create public repo**

```bash
gh repo create dpaschal/jbd-bms-dashboard --public --description "Linux dashboard for JBD/Jiabaida LiFePO4 BMS — USB/serial and BLE, real-time display, logging, alerts, simulator"
```

- [ ] **Step 2: Rename branch to main and push**

```bash
git branch -m master main
git remote add origin https://github.com/dpaschal/jbd-bms-dashboard.git
git push -u origin main
```

- [ ] **Step 3: Verify**

```bash
gh repo view dpaschal/jbd-bms-dashboard
```
Expected: repo page shown with README.

---

## Self-Review

**Spec coverage check:**
- ✅ USB/serial transport — Task 7
- ✅ BLE transport — Task 8
- ✅ Single-window all-in-one UI — Tasks 10–11
- ✅ Cell voltage display with color coding — Task 11 (CellsWidget)
- ✅ FET status + protection flags — Task 11 (FetsFlagsWidget)
- ✅ Live pyqtgraph chart — Task 11 (LiveChart)
- ✅ SQLite logging — Task 5
- ✅ History view + CSV export — Task 11 (HistoryWidget)
- ✅ Configurable alerts — Task 6 + Task 11 (SettingsPanel)
- ✅ System tray notifications — Task 10 (MainWindow._build_tray)
- ✅ BLE scan dialog — Task 11 (BLEScanDialog)
- ✅ Simulator with 5 scenarios — Task 9
- ✅ Public GitHub repo — Task 14
- ✅ MIT license — pyproject.toml + README

**Type consistency:**
- `AlertChecker.check(info: BasicInfo, cells: CellVoltages)` — consistent across Tasks 6, 10
- `write_snapshot(conn, info: BasicInfo, cells: CellVoltages)` — consistent across Tasks 5, 10
- `Transport.frame_received` signal carries `bytes` — consistent across Tasks 7, 8, 10
- `parse_response(bytes) -> BasicInfo | CellVoltages | BMSInfo` — consistent across Tasks 3, 10

**Placeholder scan:** None found.
