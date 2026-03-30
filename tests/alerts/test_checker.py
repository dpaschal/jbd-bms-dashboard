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
    checker = AlertChecker(DEFAULT_SETTINGS)
    handler = MagicMock()
    checker.alert_triggered.connect(handler)
    checker.check(_info(), _cells(voltages=[3.21, 2.95, 3.21, 3.20]))
    handler.assert_called_once()
    title, msg = handler.call_args[0]
    assert "undervolt" in title.lower() or "undervolt" in msg.lower()


def test_overtemp_fires(qapp):
    checker = AlertChecker(DEFAULT_SETTINGS)
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
    checker.check(_info(), cells)
    assert handler.call_count == 1
