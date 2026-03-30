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
    pack_voltage: float
    current: float
    remaining_ah: float
    nominal_ah: float
    cycles: int
    soc: int
    charge_fet: bool
    discharge_fet: bool
    cell_count: int
    temp_count: int
    temps: list[float]
    protection: ProtectionFlags
    balance_bitmask: int


@dataclass
class CellVoltages:
    voltages: list[float]

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
