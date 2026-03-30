import pytest
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
