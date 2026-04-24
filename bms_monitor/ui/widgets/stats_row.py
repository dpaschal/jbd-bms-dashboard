from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout, QFrame, QGridLayout
from PyQt6.QtCore import Qt
from bms_monitor.protocol.frames import BasicInfo
from bms_monitor.config import format_temp


class _Tile(QFrame):
    def __init__(self, label: str):
        super().__init__()
        self.setFrameShape(QFrame.Shape.Box)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        self._label = QLabel(label)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("color: #888; font-size: 10px;")
        self._value = QLabel("--")
        self._value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self._label)
        layout.addWidget(self._value)

    def set_value(self, text: str, color: str = "#4ecdc4") -> None:
        self._value.setText(text)
        self._value.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color};")


class _SmallTile(QFrame):
    """Compact tile for secondary info like individual temp sensors."""
    def __init__(self, label: str):
        super().__init__()
        self.setFrameShape(QFrame.Shape.Box)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        self._label = QLabel(label)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("color: #888; font-size: 9px;")
        self._value = QLabel("--")
        self._value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self._label)
        layout.addWidget(self._value)

    def set_value(self, text: str, color: str = "#ffeaa7") -> None:
        self._value.setText(text)
        self._value.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")


class StatsRow(QWidget):
    def __init__(self):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setSpacing(4)
        outer.setContentsMargins(0, 0, 0, 0)

        # Primary stats row
        row1 = QHBoxLayout()
        row1.setSpacing(6)
        self._voltage = _Tile("PACK VOLTAGE")
        self._charge_current = _Tile("CHARGE (IN)")
        self._discharge_current = _Tile("DISCHARGE (OUT)")
        self._power = _Tile("POWER")
        self._soc = _Tile("SOC")
        self._remain = _Tile("REMAINING")
        self._cycles = _Tile("CYCLES")
        self._delta = _Tile("CELL Δ")
        for tile in (self._voltage, self._charge_current, self._discharge_current,
                     self._power, self._soc, self._remain, self._cycles, self._delta):
            row1.addWidget(tile)
        outer.addLayout(row1)

        # Temperature row (up to 4 sensors)
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        self._temp_tiles: list[_SmallTile] = []
        for i in range(4):
            tile = _SmallTile(f"TEMP {i + 1}")
            self._temp_tiles.append(tile)
            row2.addWidget(tile)
        row2.addStretch()
        outer.addLayout(row2)
        self._temp_unit: str = "F"

    def set_temp_unit(self, unit: str) -> None:
        self._temp_unit = unit if unit in ("C", "F") else "F"

    def update(self, info: BasicInfo) -> None:
        self._voltage.set_value(f"{info.pack_voltage:.2f}V")

        # Split current into charge (in) and discharge (out)
        if info.current > 0:
            self._charge_current.set_value(f"{info.current:.1f}A", "#4ecdc4")
            self._discharge_current.set_value("0.0A", "#555")
        elif info.current < 0:
            self._charge_current.set_value("0.0A", "#555")
            self._discharge_current.set_value(f"{abs(info.current):.1f}A", "#f5a623")
        else:
            self._charge_current.set_value("0.0A", "#555")
            self._discharge_current.set_value("0.0A", "#555")

        # Power in watts
        power = info.pack_voltage * info.current
        if power >= 0:
            self._power.set_value(f"{power:.1f}W", "#4ecdc4")
        else:
            self._power.set_value(f"{abs(power):.1f}W", "#f5a623")

        self._soc.set_value(f"{info.soc}%", "#45b7d1")
        self._remain.set_value(f"{info.remaining_ah:.1f}/{info.nominal_ah:.0f}Ah", "#96ceb4")
        self._cycles.set_value(str(info.cycles), "#a29bfe")

        # All temperature sensors
        for i, tile in enumerate(self._temp_tiles):
            if i < len(info.temps):
                temp = info.temps[i]
                t_color = "#e94560" if temp > 40 else "#ffeaa7"
                tile.set_value(format_temp(temp, self._temp_unit), t_color)
                tile.setVisible(True)
            else:
                tile.setVisible(False)

        # Cell delta (will be set from MainWindow when CellVoltages available)
        self._delta.set_value("--", "#888")

    def update_delta(self, delta_mv: float) -> None:
        if delta_mv > 20:
            color = "#e94560"
        elif delta_mv > 10:
            color = "#ffeaa7"
        else:
            color = "#4ecdc4"
        self._delta.set_value(f"{delta_mv:.0f}mV", color)
