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
    nominal_ah REAL,
    temp1 REAL,
    temp2 REAL,
    temps TEXT,
    cycles INTEGER,
    cell_voltages TEXT,
    balance_mask INTEGER,
    charge_fet INTEGER,
    discharge_fet INTEGER,
    protection_flags TEXT
);
CREATE INDEX IF NOT EXISTS idx_ts ON snapshots(ts);
"""

_MIGRATIONS = [
    "ALTER TABLE snapshots ADD COLUMN nominal_ah REAL",
    "ALTER TABLE snapshots ADD COLUMN temps TEXT",
    "ALTER TABLE snapshots ADD COLUMN balance_mask INTEGER",
]


def open_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    for stmt in _MIGRATIONS:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError:
            pass
    conn.commit()
    return conn


def write_snapshot(conn: sqlite3.Connection, info: BasicInfo, cells: CellVoltages) -> None:
    p = info.protection
    protection_json = json.dumps({
        "cell_overvolt": p.cell_overvolt,
        "cell_undervolt": p.cell_undervolt,
        "pack_overvolt": p.pack_overvolt,
        "pack_undervolt": p.pack_undervolt,
        "charge_overcurrent": p.charge_overcurrent,
        "discharge_overcurrent": p.discharge_overcurrent,
        "short_circuit": p.short_circuit,
        "ic_error": p.ic_error,
        "mos_lock": p.mos_lock,
    })
    conn.execute(
        """INSERT INTO snapshots
           (ts, pack_voltage, current, soc, remaining_ah, nominal_ah,
            temp1, temp2, temps, cycles, cell_voltages,
            balance_mask, charge_fet, discharge_fet, protection_flags)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            time.time(),
            info.pack_voltage, info.current, info.soc,
            info.remaining_ah, info.nominal_ah,
            info.temps[0] if len(info.temps) > 0 else None,
            info.temps[1] if len(info.temps) > 1 else None,
            json.dumps(info.temps),
            info.cycles,
            json.dumps(cells.voltages),
            info.balance_bitmask,
            int(info.charge_fet), int(info.discharge_fet),
            protection_json,
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
