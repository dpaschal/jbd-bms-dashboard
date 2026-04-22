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


# Per-cell nominal / full / empty voltages for supported chemistries.
CHEMISTRY = {
    "lifepo4": {"nominal": 3.30, "full": 3.55, "empty": 2.80},
    "li-ion":  {"nominal": 3.70, "full": 4.20, "empty": 3.00},
}


def _checksum(payload: bytes) -> bytes:
    cs = (~sum(payload) + 1) & 0xFFFF
    return bytes([cs >> 8, cs & 0xFF])


def _make_response(reg: int, data: bytes) -> bytes:
    status = 0x00
    header = bytes([status, len(data)])
    cs = _checksum(header + data)
    return bytes([START, reg, status, len(data)]) + data + cs + bytes([END])


def _encode_basic_info(state: dict, cell_count: int, temp_count: int) -> bytes:
    pack_mv = int(state["pack_voltage"] * 100)
    current_ma = int(state["current"] * 100)
    remaining = int(state["remaining_ah"] * 100)
    nominal = int(state["nominal_ah"] * 100)
    bal_low = state.get("balance_mask", 0) & 0xFFFF
    bal_high = (state.get("balance_mask", 0) >> 16) & 0xFFFF
    data = struct.pack(
        ">HhHHHHHHH",
        pack_mv, current_ma, remaining, nominal,
        state["cycles"], 0x0000, bal_low, bal_high,
        state["protection_mask"],
    )
    fet = 0x03 if not state.get("fet_off") else 0x00
    data += bytes([0x20, state["soc"], fet, cell_count, temp_count])
    for i in range(temp_count):
        t = state["temps"][i] if i < len(state["temps"]) else state["temps"][-1]
        temp_raw = int(t * 10 + 2731)
        data += struct.pack(">H", temp_raw)
    return data


def _encode_cell_voltages(voltages: list[float]) -> bytes:
    return b"".join(struct.pack(">H", int(v * 1000)) for v in voltages)


class BMSSimulator:
    def __init__(
        self,
        scenario: str = "normal",
        cell_count: int = 4,
        chemistry: str = "li-ion",
        nominal_ah: float = 3.0,
        initial_soc: int = 85,
        temp_count: int = 3,
    ):
        self.scenario = scenario
        self.cell_count = cell_count
        self.chemistry = chemistry
        self.nominal_ah = nominal_ah
        self.initial_soc = initial_soc
        self.temp_count = temp_count
        self.app_port = "/tmp/bms-app"
        self.sim_port = "/tmp/bms-sim"
        self._socat: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._t0 = time.monotonic()
        self._state = self._initial_state()

    def _initial_state(self) -> dict:
        chem = CHEMISTRY[self.chemistry]
        soc = self.initial_soc
        # Per-cell voltage interpolated between empty and full by SOC.
        cell_v = chem["empty"] + (chem["full"] - chem["empty"]) * (soc / 100.0)
        pack_v = cell_v * self.cell_count
        remaining = self.nominal_ah * (soc / 100.0)
        # Small steady discharge by default; scenarios may override.
        return {
            "pack_voltage": round(pack_v, 2),
            "current": -0.5,
            "remaining_ah": round(remaining, 2),
            "nominal_ah": self.nominal_ah,
            "soc": soc,
            "temps": [25.0] * self.temp_count,
            "cycles": 12,
            "protection_mask": 0x0000,
            "balance_mask": 0,
            "fet_off": False,
        }

    def _cell_voltages(self) -> list[float]:
        base = self._state["pack_voltage"] / self.cell_count
        voltages = []
        elapsed = time.monotonic() - self._t0
        for i in range(self.cell_count):
            noise = random.gauss(0, 0.002)
            v = base + noise
            if self.scenario == "cell-drift" and i == 0:
                v -= min(elapsed * 0.001, 0.15)
            voltages.append(round(v, 3))
        return voltages

    def _tick(self) -> None:
        elapsed = time.monotonic() - self._t0
        s = self._state
        # Slow temp oscillation + per-sensor offsets so all 3 sensors differ.
        base_t = 25.0 + math.sin(elapsed / 60) * 2
        s["temps"] = [
            round(base_t + (i * 0.5), 1) for i in range(self.temp_count)
        ]

        if self.scenario == "overtemp":
            hot = min(25.0 + elapsed * 0.5, 55.0)
            s["temps"] = [round(hot + i * 0.3, 1) for i in range(self.temp_count)]

        if self.scenario == "overvoltage" and elapsed > 5:
            s["protection_mask"] = 0x0001  # cell_overvolt

        if self.scenario == "normal":
            # Gentle discharge: SOC drops ~1% every 30s, voltage sags proportionally.
            new_soc = max(0, self.initial_soc - int(elapsed / 30))
            if new_soc != s["soc"]:
                s["soc"] = new_soc
                chem = CHEMISTRY[self.chemistry]
                cell_v = chem["empty"] + (chem["full"] - chem["empty"]) * (new_soc / 100.0)
                s["pack_voltage"] = round(cell_v * self.cell_count, 2)
                s["remaining_ah"] = round(self.nominal_ah * (new_soc / 100.0), 2)
            # Occasionally set a balance bit to exercise the UI.
            if int(elapsed) % 20 < 4:
                s["balance_mask"] = 1 << (int(elapsed / 20) % self.cell_count)
            else:
                s["balance_mask"] = 0

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
            data = _encode_basic_info(self._state, self.cell_count, self.temp_count)
            port.write(_make_response(0x03, data))
        elif reg == 0x04:
            data = _encode_cell_voltages(self._cell_voltages())
            port.write(_make_response(0x04, data))
        elif reg == 0x05:
            name = f"JBD-SP{self.cell_count:02d}S{int(self.nominal_ah):03d}"
            port.write(_make_response(0x05, name.encode("ascii")))
