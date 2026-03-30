import time, subprocess, serial, pytest
from bms_monitor.simulator.simulator import BMSSimulator
from bms_monitor.protocol.parser import make_read_request, parse_response
from bms_monitor.protocol.frames import BasicInfo, CellVoltages


def test_simulator_responds_to_basic_info():
    sim = BMSSimulator(scenario="normal", cell_count=4)
    sim.start()
    time.sleep(0.5)
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
