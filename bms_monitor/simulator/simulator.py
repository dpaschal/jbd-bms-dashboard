from __future__ import annotations
import math
import os
import random
import serial
import struct
import subprocess
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
            "current": -5.0,
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
                v -= min(elapsed * 0.001, 0.15)
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
            return
        if reg == 0x03:
            data = _encode_basic_info(self._state, self.cell_count)
            port.write(_make_response(0x03, data))
        elif reg == 0x04:
            data = _encode_cell_voltages(self._cell_voltages())
            port.write(_make_response(0x04, data))
        elif reg == 0x05:
            port.write(_make_response(0x05, b"JBD-SP04S034"))
