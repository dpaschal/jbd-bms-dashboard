from __future__ import annotations
import time
from PyQt6.QtCore import QObject, pyqtSignal
from bms_monitor.protocol.frames import BasicInfo, CellVoltages

RATE_LIMIT_SECONDS = 60.0


class AlertChecker(QObject):
    alert_triggered = pyqtSignal(str, str)

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
