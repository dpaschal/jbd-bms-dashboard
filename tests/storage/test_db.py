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
