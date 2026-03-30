from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout, QFrame
from PyQt6.QtCore import Qt
from bms_monitor.protocol.frames import BasicInfo


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


class StatsRow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)
        self._voltage = _Tile("PACK VOLTAGE")
        self._current = _Tile("CURRENT")
        self._soc     = _Tile("SOC")
        self._remain  = _Tile("REMAINING")
        self._temp    = _Tile("TEMP 1")
        self._cycles  = _Tile("CYCLES")
        for tile in (self._voltage, self._current, self._soc,
                     self._remain, self._temp, self._cycles):
            layout.addWidget(tile)

    def update(self, info: BasicInfo) -> None:
        self._voltage.set_value(f"{info.pack_voltage:.1f}V")
        color = "#f5a623" if info.current >= 0 else "#4ecdc4"
        self._current.set_value(f"{info.current:+.1f}A", color)
        self._soc.set_value(f"{info.soc}%", "#45b7d1")
        self._remain.set_value(f"{info.remaining_ah:.1f}Ah", "#96ceb4")
        temp = info.temps[0] if info.temps else 0
        t_color = "#e94560" if temp > 40 else "#ffeaa7"
        self._temp.set_value(f"{temp:.1f}°C", t_color)
        self._cycles.set_value(str(info.cycles), "#a29bfe")
