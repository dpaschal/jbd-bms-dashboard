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
